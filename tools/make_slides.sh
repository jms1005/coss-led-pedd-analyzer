#!/bin/sh
# 슬라이드 HTML -> PNG(2560x1440) -> 테마별 시안 pptx
#
# render_figures.sh 와 같은 방식이다. 한글이 섞인 경로에서 file:// URL 이
# 깨지므로 임시 ASCII 경로로 복사한 뒤 렌더하고 결과만 되가져온다.
#
# 실행:  sh tools/make_slides.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_slides"
OUT="$ROOT/제출물/디자인시안"

python "$ROOT/tools/make_slides.py"

rm -rf "$TMP"; mkdir -p "$TMP" "$OUT"
cp "$ROOT"/figures/slides/* "$TMP/"
cp "$ROOT"/figures/png/*.png "$TMP/"    # 도면형 슬라이드가 참조한다
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

N=0
for f in "$TMP"/*.html; do
  NAME=$(basename "$f" .html)
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --screenshot="$TMP/$NAME.png" --window-size=2560,1440 \
    "file:///$WINTMP/$NAME.html" >/dev/null 2>&1
  cp "$TMP/$NAME.png" "$OUT/"
  N=$((N+1))
done
echo "생성: 제출물/디자인시안/ PNG ${N}장 (2560x1440)"

python "$ROOT/tools/make_slides.py" --pptx
