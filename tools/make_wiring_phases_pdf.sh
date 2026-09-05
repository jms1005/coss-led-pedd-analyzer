#!/bin/sh
# Phase 2 · Phase 4 배선도 SVG -> A4 2페이지 PDF 2종
#   docs/배선도_Phase2.pdf, docs/배선도_Phase4.pdf
#
# make_wiring_phase1_pdf.sh 와 같은 방식이다. 한글이 섞인 경로에서 file://
# URL 이 깨지므로 임시 ASCII 경로로 복사한 뒤 변환하고 결과만 되가져온다.
#
# 실행:  sh tools/make_wiring_phases_pdf.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_wiring_phases_pdf"

python "$ROOT/tools/make_wiring_phases.py"

rm -rf "$TMP"; mkdir -p "$TMP"
cp "$ROOT/figures/wiring/phase2_1.svg" "$ROOT/figures/wiring/phase2_2.svg" \
   "$ROOT/figures/wiring/phase4_1.svg" "$ROOT/figures/wiring/phase4_2.svg" \
   "$ROOT/figures/wiring/print_phase2.html" \
   "$ROOT/figures/wiring/print_phase4.html" "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

mkdir -p "$ROOT/docs"
for PH in 2 4; do
  "$CHROME" --headless --disable-gpu --no-sandbox \
    --print-to-pdf="$TMP/phase$PH.pdf" --no-pdf-header-footer \
    "file:///$WINTMP/print_phase$PH.html" >/dev/null 2>&1

  cp "$TMP/phase$PH.pdf" "$ROOT/docs/배선도_Phase$PH.pdf"

  # 페이지 수 확인. 한글 경로를 파이썬에 넘기면 깨지므로 파이프로 넣는다.
  PAGES=$(cat "$ROOT/docs/배선도_Phase$PH.pdf" | python -c "
import sys, re
print(len(re.findall(rb'/Type\s*/Page[^s]', sys.stdin.buffer.read())))
")
  echo "generated: docs/배선도_Phase$PH.pdf (${PAGES} pages)"
  if [ "$PAGES" != "2" ]; then
    echo "warning: 2 pages expected. check print_phase$PH.html" >&2
  fi
done
