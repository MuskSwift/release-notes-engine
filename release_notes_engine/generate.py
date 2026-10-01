"""Generation backends and changelog prompt for Release Notes Engine v0."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

from .validate import REQUIRED_HEADINGS

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL = "grok-4.6"
GROK_BIN_DIR = os.path.join(os.path.expanduser("~"), ".grok", "bin")

FIRST_HEADING = "## 用户可见变化"
HEADING_BLOCK = "\n".join(REQUIRED_HEADINGS)

SYSTEM_PROMPT = f"""你是面向最终用户的发布说明（changelog）撰稿器。只输出一份 Markdown 发布说明，不要任何前言、后记、解释、问候或标题以外的内容。

必须且只能使用以下 5 个 H2 标题，顺序固定，文字必须完全一致（不得翻译、改写、增删标点或换成别的级别）：

{HEADING_BLOCK}

内容规则：
- 全文使用中文。
- 不要用 markdown 代码围栏把整篇文档包起来。
- 「用户可见变化」只写最终用户能感知的功能、行为与体验变化（新增、变更、修复）。不要写内部实现、排期、会议结论或选型过程。
- 「为什么重要」用要点说明对用户的价值，最多 3 条。
- 「破坏性 / 迁移」写明不兼容变更与迁移步骤；若没有破坏性变更，该节正文只写「无」。
- 「已知限制」列出当前版本仍存在的限制、缺口或未覆盖场景。
- 「明确不写」列出本次发布说明故意不收录的内容（内部细节、未发布计划、禁忌项等）。
- 面向最终用户沟通版本变化：写他们能感知的行为、价值、迁移与限制。
- 若用户提供了禁忌清单，输出中不得出现清单禁止的内容。
- 材料中出现的 `## …` 标题字符串保持原文；不得把本引擎五个 H2 文案投射进对外部系统的描述。引用第三方产品或材料里的标题时，必须使用材料中的原文（例如 `## 问题陈述`），不得改写成 `## 用户可见变化`、`## 为什么重要`、`## 破坏性 / 迁移`、`## 已知限制`、`## 明确不写`。本引擎输出文档结构仍必须且只能是上述五个 H2，不得改动。
"""

USER_TEMPLATE = """请根据以下变更说明，生成面向最终用户的发布说明。

# 变更说明
{notes}

# 禁忌
{taboo}
"""


def build_user_prompt(notes: str, taboo: str) -> str:
    taboo_text = taboo.strip() if taboo and taboo.strip() else "（无）"
    return USER_TEMPLATE.format(
        notes=notes.strip(),
        taboo=taboo_text,
    )


def combined_prompt(notes: str, taboo: str) -> str:
    return SYSTEM_PROMPT + "\n\n" + build_user_prompt(notes, taboo)


def strip_wrapping_fences(text: str) -> str:
    """Remove a single markdown fence wrapping the whole document, if present."""
    body = text.strip()
    if not body.startswith("```"):
        return body
    lines = body.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def strip_leading_preamble(markdown: str) -> str:
    """Slice from the first exact ``## 用户可见变化`` so the file starts at that heading."""
    idx = markdown.find(FIRST_HEADING)
    if idx == -1:
        return markdown
    return markdown[idx:].lstrip()


def generate(notes: str, taboo: str = "") -> str:
    """Generate changelog markdown via xAI API (if XAI_API_KEY) or grok CLI fallback."""
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if api_key:
        return _generate_via_api(notes, taboo, api_key)
    return _generate_via_grok_cli(notes, taboo)


def _generate_via_api(notes: str, taboo: str, api_key: str) -> str:
    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(notes, taboo)},
        ],
        "stream": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        XAI_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI API HTTP {exc.code}: {err_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"xAI API request failed: {exc}") from exc

    try:
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"xAI API returned unexpected payload: {raw[:2000]}") from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("xAI API returned empty content")
    return content


def _generate_via_grok_cli(notes: str, taboo: str) -> str:
    env = os.environ.copy()
    env["PATH"] = GROK_BIN_DIR + os.pathsep + env.get("PATH", "")
    prompt = combined_prompt(notes, taboo)
    cmd = [
        "grok",
        "-p",
        prompt,
        "-m",
        XAI_MODEL,
        "--effort",
        "high",
        "--always-approve",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "grok CLI not found. Set XAI_API_KEY or install grok at ~/.grok/bin"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("grok CLI timed out") from exc

    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"grok CLI failed (exit {result.returncode}): {err}")

    stdout = (result.stdout or "").strip()
    if not stdout:
        raise RuntimeError("grok CLI returned empty stdout")
    return stdout
