/*
 * button.c — 디바운스와 짧게/길게 판정
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
  BTN_PORT |= (uint8_t)(1 << BTN_BIT);   /* 내부 풀업 */
  g_held = 0;
  g_long_fired = 0;
}

button_event_t button_poll(void) {
  /* 풀업이므로 눌리면 LOW */
  uint8_t pressed = (uint8_t)((BTN_PIN & (1 << BTN_BIT)) ? 0 : 1);

  if (pressed) {
    if (g_held < 0xFFFF) {
      g_held++;
    }
    if (!g_long_fired && g_held >= BUTTON_LONG_TICKS) {
      g_long_fired = 1;
      return BTN_LONG;
    }
    return BTN_NONE;
  }

  /* 떼어진 순간 */
  if (g_held > 0) {
    uint8_t  was_long = g_long_fired;
    uint16_t held = g_held;
    g_held = 0;
    g_long_fired = 0;
    /* 1틱(20ms) 미만은 채터링으로 간주해 버린다 */
    if (!was_long && held >= 1) {
      return BTN_SHORT;
    }
  }
  return BTN_NONE;
}
