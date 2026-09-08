#!/bin/sh
# 마크다운 문서 -> A4 PDF
#
# make_wiring_pdf.sh 와 같은 방식이다. 한글이 섞인 경로에서 file:// URL 이
# 깨지므로 임시 ASCII 경로에서 변환하고 결과만 되가져온다. 또한 chrome.exe
# 와 python 은 Windows 프로그램이라 "/c/Users/..." 를 못 읽으므로, 이들에게
# 넘기는 경로는 전부 $WINTMP(윈도우 경로)를 쓴다.
#
# 실행:  sh tools/make_doc_pdf.sh docs/페이즈별_회로_동작.md
#        sh tools/make_doc_pdf.sh docs/판별_로직_설명.md docs/다른이름.pdf
#
# 인자를 주지 않으면 아래 DEFAULT_DOCS 를 전부 만든다.
# **경로는 둘 다 저장소 루트 기준 상대 경로다** (다른 PDF 스크립트와 동일).
# 절대 경로를 주면 $ROOT 가 앞에 붙어 엉뚱한 곳을 가리킨다.
# 출력 경로를 생략하면 입력의 .md 를 .pdf 로 바꾼 이름을 쓴다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHROME="/c/Program Files/Google/Chrome/Application/chrome.exe"
TMP="${TMPDIR:-/tmp}/pedd_doc_pdf"

DEFAULT_DOCS="docs/페이즈별_회로_동작.md"

if [ -n "$1" ]; then
  DOCS="$1"
  OUTARG="$2"
else
  DOCS="$DEFAULT_DOCS"
  OUTARG=""
fi

rm -rf "$TMP"; mkdir -p "$TMP"
WINTMP=$(cd "$TMP" && pwd -W 2>/dev/null || echo "$TMP")

for SRC in $DOCS; do
  if [ ! -f "$ROOT/$SRC" ]; then
    echo "없는 파일: $SRC" >&2
    exit 1
  fi

  # 한글 파일명이 file:// URL 에서 깨지므로 임시로 ASCII 이름을 쓴다.
  cp "$ROOT/$SRC" "$TMP/doc.md"
  python "$ROOT/tools/md_to_html.py" "$WINTMP/doc.md" "$WINTMP/doc.html" \
    >/dev/null

  "$CHROME" --headless --disable-gpu --no-sandbox \
    --print-to-pdf="$WINTMP/doc.pdf" --no-pdf-header-footer \
    "file:///$WINTMP/doc.html" >/dev/null 2>&1

  if [ ! -f "$TMP/doc.pdf" ]; then
    echo "실패: PDF 가 만들어지지 않았습니다 (Chrome 경로를 확인하세요)" >&2
    exit 1
  fi

  if [ -n "$OUTARG" ]; then
    OUT="$OUTARG"
  else
    OUT=$(echo "$SRC" | sed 's/\.md$/.pdf/')
  fi
  cp "$TMP/doc.pdf" "$ROOT/$OUT"

  # 페이지 수 확인. 한글 경로를 파이썬 인자로 넘기면 깨지므로 파이프로 넣는다.
  PAGES=$(cat "$ROOT/$OUT" | python -c "
import sys, re
print(len(re.findall(rb'/Type\s*/Page[^s]', sys.stdin.buffer.read())))
")
  echo "생성: $OUT (${PAGES}페이지)"
done
