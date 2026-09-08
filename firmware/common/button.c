/*
 * button.c — 디바운스와 짧게/길게 판정
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * 스위치는 눌리는 찰나에 금속 접점이 미세하게 여러 번 튄다. 사람 눈에는
 * 한 번이지만 MCU 에게는 수 ms 사이에 눌림/떼임이 수십 번 오간 것으로
 * 보인다. 이걸 그대로 세면 한 번 눌렀는데 여러 번 눌린 것이 된다.
 * 이 튐을 걸러내는 것을 디바운스라고 한다.
 *
 * 여기서는 타이머나 인터럽트 없이, main.c 가 20ms 마다 button_poll() 을
 * 부르는 것으로 해결한다. 20ms 는 접점이 튀는 시간(보통 1~2ms)보다 훨씬
 * 길어서, 튐이 끝난 뒤의 안정된 상태만 보게 된다. 이 함수에서 말하는
 * "틱" 1회가 곧 20ms 다 (BUTTON_POLL_MS, button.h).
 *
 * 길게 누름은 틱을 세는 것으로 판정한다. 100틱 = 2초.
 */

#include <avr/io.h>

#include "button.h"

#define BTN_DDR   DDRD
#define BTN_PORT  PORTD
#define BTN_PIN   PIND
#define BTN_BIT   PD2

/* 눌린 상태로 지난 폴링 횟수. 0이면 떼어져 있음 */
static uint16_t g_held = 0;
/* 길게가 이미 발동했으면 뗄 때 짧게로 또 세지 않는다 */
static uint8_t  g_long_fired = 0;

void button_init(void) {
  BTN_DDR  &= (uint8_t)~(1 << BTN_BIT);  /* 입력 */
  /*
   * 내부 풀업을 켠다. MCU 안에 들어 있는 저항이 이 핀을 평소 5V 로
   * 끌어올려 둔다는 뜻이다. 스위치는 핀과 GND 사이에 있으므로, 누르면
   * 핀이 GND 로 직결되어 0V 가 된다. 덕분에 외부 저항이 필요 없다.
   */
  BTN_PORT |= (uint8_t)(1 << BTN_BIT);
  g_held = 0;
  g_long_fired = 0;
}

button_event_t button_poll(void) {
  /* 위 풀업 때문에 논리가 뒤집혀 있다. 핀이 HIGH = 떼어짐, LOW = 눌림. */
  uint8_t pressed = (uint8_t)((BTN_PIN & (1 << BTN_BIT)) ? 0 : 1);

  if (pressed) {
    /* 계속 눌려 있는 동안 틱을 센다. 상한에서 멈춰 되감김을 막는다. */
    if (g_held < 0xFFFF) {
      g_held++;
    }
    /*
     * 2초를 채우는 순간 떼기를 기다리지 않고 바로 알린다. 사용자가 화면
     * 반응을 보고 손을 떼면 되므로, 얼마나 더 누르고 있어야 하는지
     * 짐작할 필요가 없다. g_long_fired 로 한 번만 발동시킨다.
     */
    if (!g_long_fired && g_held >= BUTTON_LONG_TICKS) {
      g_long_fired = 1;
      return BTN_LONG;
    }
    return BTN_NONE;
  }

  /*
   * 여기부터는 떼어져 있는 상태. g_held 가 0 보다 크다면 "직전 틱까지는
   * 눌려 있었다" 는 뜻이므로, 지금이 바로 뗀 순간이다.
   * 길게가 이미 발동했다면 짧게로 또 세지 않고 조용히 정리만 한다.
   */
  if (g_held > 0) {
    uint8_t was_long = g_long_fired;
    g_held = 0;
    g_long_fired = 0;
    /*
     * 채터링은 별도 조건으로 거르지 않는다. 폴링 간격 자체가 20ms 라서,
     * 접점이 튀는 1~2ms 동안 일어난 일은 애초에 이 함수가 보지 못한다.
     * 여기까지 왔다는 것은 "폴링 시점에 눌려 있는 것을 최소 한 번 봤고
     * 지금은 떼어져 있다" 는 뜻이므로 그대로 짧게 누름으로 친다.
     */
    if (!was_long) {
      return BTN_SHORT;
    }
  }
  return BTN_NONE;
}
