#!/bin/sh
# 구매 목록 HTML -> docs/구매목록.pdf (A4 1페이지)
#
# 한글이 섞인 경로에서 file:// URL 이 깨지므로 임시 ASCII 경로로 복사한 뒤
# 변환하고 결과만 되가져온다. make_pdf.sh 와 같은 방식이다.
#
# 실행:  sh tools/make_shopping_pdf.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_shopping"

rm -rf "$TMP"; mkdir -p "$TMP"
cp "$ROOT/figures/shopping/print.html" "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

"$CHROME" --headless --disable-gpu --no-sandbox --print-to-pdf="$TMP/shopping.pdf" --no-pdf-header-footer "file:///$WINTMP/print.html" >/dev/null 2>&1

mkdir -p "$ROOT/docs"
cp "$TMP/shopping.pdf" "$ROOT/docs/구매목록.pdf"

PAGES=$(cat "$ROOT/docs/구매목록.pdf" | python -c "
import sys, re
print(len(re.findall(rb'/Type\s*/Page[^s]', sys.stdin.buffer.read())))
")
echo "생성: docs/구매목록.pdf (${PAGES}페이지)"
