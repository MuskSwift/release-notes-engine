# Release Notes Engine

CLI that turns **change notes** (plus an optional taboo list) into a Markdown changelog for end users. Output is Chinese. The five H2 headings are a stable contract so reviews and diffs can key off structure.

Python **3.10+**, standard library only — no pip packages required. Licensed under MIT.

## Five H2 contract (exact, in order)

Generated changelogs must contain these heading strings, exactly, in this order:

1. `## 用户可见变化`
2. `## 为什么重要`
3. `## 破坏性 / 迁移`
4. `## 已知限制`
5. `## 明确不写`

Do not translate, rephrase, retitle, or change heading level. Body wording may vary between runs.

Content rules the model is instructed to follow:

- 「为什么重要」: at most **3** bullets.
- 「破坏性 / 迁移」: write **「无」** when there is no breaking change.
- Honour the taboo list when provided.
- Write in Chinese. Output is a user-facing changelog, not a decision memo.
- Cited third-party `## …` headings from materials stay verbatim (do not rewrite them as this engine’s five H2).

## Install

From the repo root (no install):

```bash
python3 -m release_notes_engine --help
```

(`python -m release_notes_engine` works when `python` is 3.10+.)

Optional editable install (exposes the `release-notes-engine` console script):

```bash
pip install -e .
```

## Authentication (bring your own)

Generation uses model **grok-4.7-build-fast**. This project does not ship API keys or implement login.

**Option A — xAI HTTP API (used when a key is present).** Set `XAI_API_KEY` in the environment. The CLI POSTs to `https://api.x.ai/v1/chat/completions` with stdlib `urllib.request`.

```bash
export XAI_API_KEY="xai-..."
```

**Option B — grok CLI fallback.** If `XAI_API_KEY` is unset, the CLI shells out to an already-authenticated grok CLI (typically at `~/.grok/bin`):

```bash
export PATH="$HOME/.grok/bin:$PATH"
grok -p "<prompt>" -m grok-4.7-build-fast --effort xhigh --always-approve
```

Authenticate the grok CLI yourself before running this tool. If neither a key nor `grok` is available, generation fails.

## End-to-end example

From the repo root, using the bundled fixtures:

```bash
python3 -m release_notes_engine \
  --notes-file examples/sample-input.md \
  --taboo-file examples/taboo-sample.txt \
  --out out/qingdanxia-v240-release-notes.md
```

On success the CLI prints the output path (`out/qingdanxia-v240-release-notes.md`) and exits `0`. Open that file: it should **start at** `## 用户可见变化` and include all five headings.

Inline notes are accepted:

```bash
python3 -m release_notes_engine --notes "v1.2：搜索支持拼音；修复深色模式下按钮对比度。"
```

`--notes` and `--notes-file` can be combined (concatenated). At least one notes source is required. `--taboo` / `--taboo-file` are optional.

Default output path: `./out/<slug>-release-notes.md`. The slug is derived from the notes text (first non-empty line; spaces → `-`; unsafe characters stripped; CJK kept).

## Example paths

| Path | What it is |
| --- | --- |
| [`examples/sample-input.md`](examples/sample-input.md) | Change-notes fixture (new/changed/fixed/breaking drafts) |
| [`examples/taboo-sample.txt`](examples/taboo-sample.txt) | Optional taboo / forbidden-content list |
| [`examples/sample-output.md`](examples/sample-output.md) | Hand-written sample changelog in the five-heading shape |

## Post-processing

After generation:

1. A wrapping markdown fence (if the model added one, including ` ```markdown `) is stripped.
2. Any leading preamble **before** the first exact `## 用户可见变化` is sliced off so the saved file starts at that heading.
3. All five heading strings are checked with exact substring match. If any is missing, the CLI exits non-zero and **unlinks** the output file.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Changelog written; all five headings present. stdout is the output path. |
| `1` | Input error, generation failure, empty output, or missing headings. Missing headings are listed on stderr; a failed output file is removed. |
| `130` | Interrupted (`Ctrl-C`). |

## Re-run heading assert

From the repo root:

```bash
bash scripts/assert_stable_headings.sh
```

The script runs `python3 -m release_notes_engine --notes-file examples/sample-input.md` twice into temp files, and asserts that all five release-notes heading strings appear in **each** output (body wording may differ). Prints `PASS` or `FAIL` and exits `0` / `1`. Requires a working backend (`XAI_API_KEY` or authenticated `grok` CLI).

## License

[MIT](LICENSE).
