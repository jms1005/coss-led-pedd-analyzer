#!/bin/sh
# Phase 1 배선도 SVG 1장 -> A4 1페이지 PDF (docs/배선도_Phase1.pdf)
#
# make_wiring_pdf.sh 와 같은 방식이다. 한글이 섞인 경로에서 file:// URL 이
# 깨지므로 임시 ASCII 경로로 복사한 뒤 변환하고 결과만 되가져온다.
#
# 실행:  sh tools/make_wiring_phase1_pdf.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_wiring_phase1_pdf"

python "$ROOT/tools/make_wiring_phase1.py"

rm -rf "$TMP"; mkdir -p "$TMP"
cp "$ROOT/figures/wiring/phase1.svg" "$TMP/"
cp "$ROOT/figures/wiring/print_phase1.html" "$TMP/print_phase1.html"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

"$CHROME" --headless --disable-gpu --no-sandbox \
  --print-to-pdf="$TMP/phase1.pdf" --no-pdf-header-footer \
  "file:///$WINTMP/print_phase1.html" >/dev/null 2>&1

mkdir -p "$ROOT/docs"
cp "$TMP/phase1.pdf" "$ROOT/docs/배선도_Phase1.pdf"

# 페이지 수 확인. 한글 경로를 파이썬에 넘기면 깨지므로 파이프로 넣는다.
PAGES=$(cat "$ROOT/docs/배선도_Phase1.pdf" | python -c "
import sys, re
print(len(re.findall(rb'/Type\s*/Page[^s]', sys.stdin.buffer.read())))
")
echo "generated: docs/배선도_Phase1.pdf (${PAGES} page)"
if [ "$PAGES" != "1" ]; then
  echo "warning: 1 page expected. check print_phase1.html" >&2
fi
