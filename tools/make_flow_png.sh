#!/bin/sh
# 전기 흐름 그림 SVG 3장 -> 2배 배율 PNG (figures/flow/png/)
#
# render_figures.sh 와 같은 방식이다. 다른 점은 두 가지.
#   - 크기가 장마다 달라서 viewBox 를 읽어 창 크기를 정한다
#   - 한글이 섞인 경로에서 file:// URL 이 깨지므로 임시 ASCII 경로에서
#     변환하고 결과만 되가져온다 (make_wiring_pdf.sh 와 동일)
#
# PNG 가 따로 필요한 이유: GitHub 는 마크다운 안의 SVG 를 보안 필터를 거쳐
# 보여주는데, 이때 글꼴이 시스템 기본으로 바뀌어 글자 간격이 달라질 수 있다.
# 문서(docs/쉬운_설명.md)는 PNG 를 참조해 어디서 보든 같게 나오도록 한다.
# SVG 는 인쇄·슬라이드용으로 그대로 남겨 둔다.
#
# 실행:  sh tools/make_flow_png.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_flow_png"

python "$ROOT/tools/make_flow_drawings.py"

rm -rf "$TMP"; mkdir -p "$TMP" "$ROOT/figures/flow/png"
cp "$ROOT"/figures/flow/flow*.svg "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

for f in flow1 flow2 flow3; do
  # 파이썬은 Windows 쪽 실행 파일이라 /c/... 형태의 POSIX 경로를 못 읽는다.
  # 그래서 $TMP 가 아니라 변환해 둔 $WINTMP 를 넘긴다.
  DIM=$(python -c "
import re, io
s = io.open(r'$WINTMP/$f.svg', encoding='utf-8').read(600)
m = re.search(r'viewBox=\"0 0 (\d+) (\d+)\"', s)
print('%s %s' % (m.group(1), m.group(2)))
")
  W=$(echo $DIM | cut -d' ' -f1); H=$(echo $DIM | cut -d' ' -f2)
  printf '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}img{display:block;width:%dpx}</style><img src="%s.svg">' \
    $((W*2)) "$f" > "$TMP/$f.html"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --screenshot="$TMP/$f.png" --window-size=$((W*2)),$((H*2)) \
    "file:///$WINTMP/$f.html" >/dev/null 2>&1
  cp "$TMP/$f.png" "$ROOT/figures/flow/png/"
  echo "생성: figures/flow/png/$f.png (${W}x${H} -> $((W*2))x$((H*2)))"
done
