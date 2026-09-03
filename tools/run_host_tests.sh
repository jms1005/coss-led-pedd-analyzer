#!/bin/sh
# classify 모듈을 PC에서 컴파일해 실행한다. AVR 하드웨어가 필요 없다.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT="$ROOT/tools/test_classify.exe"

# winget 이 등록한 PATH 는 새 셸부터 적용된다. 없으면 절대 경로로 넘어간다.
GCC=gcc
if ! command -v gcc >/dev/null 2>&1; then
  GCC="/c/Users/hwali/AppData/Local/Microsoft/WinGet/Packages/BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe/mingw64/bin/gcc.exe"
fi

"$GCC" -std=c99 -Wall -Wextra -O1 \
    -I"$ROOT/firmware/common" \
    -o "$OUT" \
    "$ROOT/tests/test_classify.c" \
    "$ROOT/firmware/common/classify.c"
"$OUT"
