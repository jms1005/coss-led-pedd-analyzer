/*
 * button.h — PD2 택트 스위치. 폴링 + 디바운스.
 *
 * INT0 인터럽트를 쓰지 않는다. 인터럽트는 Timer1 입력 캡처 타이밍에
 * 지터를 줄 수 있고, 측정 정밀도가 이 프로젝트의 핵심이기 때문이다.
 *
 * 스위치는 핀과 GND 사이에 연결하고 내부 풀업을 쓴다. 외부 저항이 없다.
 */

#ifndef BUTTON_H
#define BUTTON_H

#include <stdint.h>

#define BUTTON_POLL_MS    20
#define BUTTON_LONG_MS    2000
#define BUTTON_LONG_TICKS (BUTTON_LONG_MS / BUTTON_POLL_MS)  /* 100 */

typedef enum {
  BTN_NONE  = 0,
  BTN_SHORT = 1,
  BTN_LONG  = 2
} button_event_t;

void button_init(void);

/*
 * BUTTON_POLL_MS 주기로 호출한다.
 * 짧게: 눌렀다 뗀 순간 반환. 길게: 2초를 채우는 순간 반환(떼기 전).
 */
button_event_t button_poll(void);

#endif /* BUTTON_H */
