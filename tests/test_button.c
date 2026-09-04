/*
 * button 모듈 단위 테스트. PC에서 실행한다.
 *
 * 브링업 2단계(버튼만 연결)에서 오동작할 때, 코드가 아니라 배선을
 * 의심할 수 있게 하는 것이 목적이다.
 */

#include <stdio.h>

#include "avr/io.h"
#include "button.h"

static int g_fail = 0;

static void check(int cond, const char *name) {
  if (cond) {
    printf("  PASS  %s\n", name);
  } else {
    printf("  FAIL  %s\n", name);
    g_fail++;
  }
}

/* 풀업이므로 눌리면 LOW */
static void down(void) { fake_pind &= (uint8_t)~(1 << PD2); }
static void up(void)   { fake_pind |= (uint8_t)(1 << PD2); }

/* n 틱 동안 폴링하며, 그 사이 반환된 이벤트 중 마지막 것을 준다 */
static button_event_t poll_n(int n) {
  button_event_t last = BTN_NONE;
  int i;
  for (i = 0; i < n; i++) {
    button_event_t e = button_poll();
    if (e != BTN_NONE) {
      last = e;
    }
  }
  return last;
}

static void setup(void) {
  up();
  button_init();
}

/* 초기화가 입력 + 내부 풀업으로 두는지 */
static void test_init(void) {
  fake_ddrd  = 0xFF;
  fake_portd = 0x00;
  button_init();
  check((fake_ddrd & (1 << PD2)) == 0, "초기화 - PD2 를 입력으로 둔다");
  check((fake_portd & (1 << PD2)) != 0, "초기화 - 내부 풀업을 켠다");
}

/* 안 누르면 아무 일도 없어야 한다 */
static void test_idle(void) {
  setup();
  check(poll_n(50) == BTN_NONE, "안 누름 - 이벤트 없음");
}

/* 짧게: 뗀 순간에만 SHORT 가 나온다 */
static void test_short(void) {
  setup();
  down();
  check(poll_n(3) == BTN_NONE, "짧게 - 누르고 있는 동안은 이벤트 없음");
  up();
  check(button_poll() == BTN_SHORT, "짧게 - 뗀 순간 SHORT");
  check(poll_n(5) == BTN_NONE, "짧게 - 그 뒤로는 조용함");
}

/* 길게: 2초(100틱)를 채우는 순간 떼기 전에 나온다 */
static void test_long(void) {
  int i;
  button_event_t e = BTN_NONE;
  setup();
  down();
  for (i = 1; i < BUTTON_LONG_TICKS; i++) {
    e = button_poll();
  }
  check(e == BTN_NONE, "길게 - 99틱까지는 이벤트 없음");
  check(button_poll() == BTN_LONG, "길게 - 100틱째에 LONG");
  check(poll_n(50) == BTN_NONE, "길게 - LONG 은 한 번만 나온다");
}

/* 길게가 나간 뒤 떼어도 SHORT 가 또 나오면 안 된다 */
static void test_long_then_release(void) {
  setup();
  down();
  poll_n(BUTTON_LONG_TICKS + 10);
  up();
  check(poll_n(5) == BTN_NONE, "길게 후 뗌 - SHORT 가 겹쳐 나오지 않음");
}

/* 짧게를 연달아 두 번 */
static void test_two_shorts(void) {
  setup();
  down();  poll_n(3);
  up();
  check(button_poll() == BTN_SHORT, "연속 - 첫 번째 SHORT");
  down();  poll_n(3);
  up();
  check(button_poll() == BTN_SHORT, "연속 - 두 번째 SHORT");
}

/*
 * 현재 구현의 확인: 한 틱짜리 입력도 SHORT 로 나간다.
 *
 * button.c 의 주석은 "1틱(20ms) 미만은 채터링으로 간주해 버린다" 고
 * 하지만, held >= 1 조건은 g_held > 0 으로 이미 걸러진 뒤라 항상 참이다.
 * 고칠지는 실물에서 채터링이 실제로 관측되는지 보고 정한다.
 * 여기서는 지금 동작을 고정해 둔다.
 */
static void test_single_tick(void) {
  setup();
  down();
  check(button_poll() == BTN_NONE, "1틱 - 누른 순간은 이벤트 없음");
  up();
  check(button_poll() == BTN_SHORT, "1틱 - 현재 구현은 SHORT 를 낸다");
}

int main(void) {
  printf("== button 단위 테스트 ==\n");
  test_init();
  test_idle();
  test_short();
  test_long();
  test_long_then_release();
  test_two_shorts();
  test_single_tick();
  printf("== 실패 %d건 ==\n", g_fail);
  return g_fail ? 1 : 0;
}
