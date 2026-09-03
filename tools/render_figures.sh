#!/bin/sh
# SVG 도면을 2배 배율 PNG로 렌더한다. PPT·Word 삽입용.
# python-pptx 와 Word 는 SVG 를 직접 못 넣으므로 PNG 가 필요하다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_png"

rm -rf "$TMP"; mkdir -p "$TMP" "$ROOT/figures/png"
cp "$ROOT"/figures/*.svg "$TMP/"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

for f in fig1_block_diagram fig2_program_flow fig3_schematic; do
  DIM=$(python -c "
import re, io, sys
s = io.open(r'$TMP/$f.svg', encoding='utf-8').read(600)
m = re.search(r'viewBox=\"0 0 (\d+) (\d+)\"', s)
print('%s %s' % (m.group(1), m.group(2)))
")
  W=$(echo $DIM | cut -d' ' -f1); H=$(echo $DIM | cut -d' ' -f2)
  printf '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}img{display:block;width:%dpx}</style><img src="%s.svg">' \
    $((W*2)) "$f" > "$TMP/$f.html"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --screenshot="$TMP/$f.png" --window-size=$((W*2)),$((H*2)) \
    "file:///$WINTMP/$f.html" >/dev/null 2>&1
  cp "$TMP/$f.png" "$ROOT/figures/png/"
  echo "생성: figures/png/$f.png"
done
