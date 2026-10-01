#!/usr/bin/env bash
# Run the CLI twice on the same change-notes fixture; assert all 5 H2 headings exist.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

FIXTURE="$ROOT/examples/sample-input.md"
if [[ ! -f "$FIXTURE" ]]; then
  echo "FAIL: fixture missing: $FIXTURE"
  exit 1
fi

OUT1="$(mktemp "${TMPDIR:-/tmp}/release-notes-1-XXXXXX.md")"
OUT2="$(mktemp "${TMPDIR:-/tmp}/release-notes-2-XXXXXX.md")"
cleanup() { rm -f "$OUT1" "$OUT2"; }
trap cleanup EXIT

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "FAIL: python3 not found"
  exit 1
fi

run_cli() {
  local out="$1"
  "$PY" -m release_notes_engine --notes-file "$FIXTURE" --out "$out"
}

if ! run_cli "$OUT1"; then
  echo "FAIL: first CLI run failed"
  exit 1
fi
if ! run_cli "$OUT2"; then
  echo "FAIL: second CLI run failed"
  exit 1
fi

HEADINGS=(
  "## 用户可见变化"
  "## 为什么重要"
  "## 破坏性 / 迁移"
  "## 已知限制"
  "## 明确不写"
)

fail=0
for f in "$OUT1" "$OUT2"; do
  if [[ ! -s "$f" ]]; then
    echo "FAIL: empty output: $f" >&2
    fail=1
    continue
  fi
  for h in "${HEADINGS[@]}"; do
    if ! grep -qF "$h" "$f"; then
      echo "FAIL: missing heading in $f: $h" >&2
      fail=1
    fi
  done
done

if [[ "$fail" -ne 0 ]]; then
  echo "FAIL"
  exit 1
fi

echo "PASS"
exit 0
