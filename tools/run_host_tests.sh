#!/bin/sh
# 펌웨어 모듈을 PC에서 컴파일해 실행한다. AVR 하드웨어가 필요 없다.
#
#   classify  순수 계산 — 가짜 레지스터가 필요 없다
#   button    PIND 를 tests/fake 로 대체
#   store     EEPROM 레지스터를 tests/fake 로 대체
#
# 펌웨어 코드는 고치지 않는다. tests/fake 를 -I 맨 앞에 두면
# #include <avr/io.h> 가 가짜를 집는다.
#
# 실행:  sh tools/run_host_tests.sh
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BIN="$ROOT/tools/hosttest"

# winget 이 등록한 PATH 는 새 셸부터 적용된다. 없으면 절대 경로로 넘어간다.
GCC=gcc
if ! command -v gcc >/dev/null 2>&1; then
  GCC="/c/Users/hwali/AppData/Local/Microsoft/WinGet/Packages/BrechtSanders.WinLibs.POSIX.UCRT_Microsoft.Winget.Source_8wekyb3d8bbwe/mingw64/bin/gcc.exe"
fi

# 경로에 공백이 있으므로 -I 는 build_and_run 안에서 따옴표로 넘긴다.
COMMON="$ROOT/firmware/common"
FAKE="$ROOT/tests/fake/fake_io.c"

mkdir -p "$BIN"
FAILED=0

build_and_run() {
  NAME=$1
  shift
  echo ""
  "$GCC" -std=c99 -Wall -Wextra -O1 -I"$ROOT/tests/fake" -I"$COMMON" -o "$BIN/$NAME.exe" "$@"
  if "$BIN/$NAME.exe"; then
    :
  else
    FAILED=$((FAILED+1))
  fi
}

build_and_run test_classify "$ROOT/tests/test_classify.c" "$COMMON/classify.c"
build_and_run test_button   "$ROOT/tests/test_button.c"   "$COMMON/button.c" "$FAKE"
build_and_run test_store    "$ROOT/tests/test_store.c"    "$COMMON/store.c"  "$FAKE"

echo ""
if [ "$FAILED" -ne 0 ]; then
  echo "### 실패한 테스트 프로그램 ${FAILED}개 ###"
  exit 1
fi
echo "### 전체 통과 ###"
