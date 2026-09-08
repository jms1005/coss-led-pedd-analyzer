#!/bin/sh
# SVG 도면을 2배 배율 PNG로 렌더한다. PPT·Word 삽입용.
# python-pptx 와 Word 는 SVG 를 직접 못 넣으므로 PNG 가 필요하다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_png"

rm -rf "$TMP"; mkdir -p "$TMP" "$ROOT/figures/png"
cp "$ROOT"/figures/*.svg "$TMP/"

# chrome.exe 와 python 은 Windows 프로그램이라 "/c/Users/..." 를 못 읽는다.
# ("C:\c\Users\..." 로 해석해 파일을 못 찾는다) 아래부터는 Windows 경로만 쓴다.
# Git Bash 의 cp 는 "C:/Users/..." 형태도 그대로 받으므로 하나로 통일해도 된다.
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

for f in fig1_block_diagram fig2_program_flow fig3_schematic; do
  DIM=$(python -c "
import re, io, sys
s = io.open(r'$WINTMP/$f.svg', encoding='utf-8').read(600)
m = re.search(r'viewBox=\"0 0 (\d+) (\d+)\"', s)
print('%s %s' % (m.group(1), m.group(2)))
")
  W=$(echo $DIM | cut -d' ' -f1); H=$(echo $DIM | cut -d' ' -f2)
  printf '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#fff}img{display:block;width:%dpx}</style><img src="%s.svg">' \
    $((W*2)) "$f" > "$WINTMP/$f.html"
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --screenshot="$WINTMP/$f.png" --window-size=$((W*2)),$((H*2)) \
    "file:///$WINTMP/$f.html" >/dev/null 2>&1
  if [ ! -f "$WINTMP/$f.png" ]; then
    echo "실패: $f.png 가 만들어지지 않았습니다 (Chrome 경로를 확인하세요)" >&2
    exit 1
  fi
  cp "$WINTMP/$f.png" "$ROOT/figures/png/"
  echo "생성: figures/png/$f.png"
done
