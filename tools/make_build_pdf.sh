#!/bin/sh
# 제작 도면 SVG 6장 -> A4 6페이지 PDF (docs/제작도면.pdf)
#
# make_pdf.sh 와 같은 방식이다. 한글이 섞인 경로에서 file:// URL 이 깨지므로
# 임시 ASCII 경로로 복사한 뒤 변환하고 결과만 되가져온다.
#
# 실행:  sh tools/make_build_pdf.sh [--axis 20]
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_build_pdf"

python "$ROOT/tools/make_build_drawings.py" "$@"

rm -rf "$TMP"; mkdir -p "$TMP"
cp "$ROOT"/figures/build/sheet*.svg "$ROOT/figures/build/print.html" "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

"$CHROME" --headless --disable-gpu --no-sandbox \
  --print-to-pdf="$TMP/build.pdf" --no-pdf-header-footer \
  "file:///$WINTMP/print.html" >/dev/null 2>&1

mkdir -p "$ROOT/docs"
cp "$TMP/build.pdf" "$ROOT/docs/제작도면.pdf"

# 페이지 수 확인. 한글 경로를 파이썬에 넘기면 깨지므로 파이프로 넣는다.
PAGES=$(cat "$ROOT/docs/제작도면.pdf" | python -c "
import sys, re
print(len(re.findall(rb'/Type\s*/Page[^s]', sys.stdin.buffer.read())))
")
echo "생성: docs/제작도면.pdf (${PAGES}페이지)"
if [ "$PAGES" != "6" ]; then
  echo "경고: 6페이지가 아닙니다. print.html 의 페이지 나눔을 확인하세요." >&2
fi
