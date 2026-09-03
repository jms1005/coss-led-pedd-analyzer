/*
 * pedd.h — PEDD 방전 시간 측정 코어 (인터페이스)
 *
 * 계획서 3.2절(광검출 원리) / 6.1절(GPIO 상태 시퀀스) / 6.2절(레지스터 설정) 구현.
 */

#ifndef PEDD_H
#define PEDD_H

#include <stdint.h>

/* 측정 결과 상태 */
typedef enum {
  PEDD_OK      = 0,  /* 정상적으로 임계점 통과를 캡처함 */
  PEDD_TIMEOUT = 1   /* 제한 시간 내에 방전이 끝나지 않음 */
} pedd_status_t;

typedef struct {
  pedd_status_t status;
  uint32_t      ticks;     /* 방전 시간. 1틱 = 500ns (프리스케일러 /8, 16MHz) */
  uint16_t      overflows; /* Timer1 오버플로우 발생 횟수 (진단용) */
} pedd_result_t;

/* 발광 LED 채널 식별자. Phase 1에서는 CH_R 하나만 사용한다. */
typedef enum {
  PEDD_CH_DARK = 0,  /* 전체 소등 — 암전류 / 환경광 측정용 */
  PEDD_CH_R    = 1,
  PEDD_CH_G    = 2,
  PEDD_CH_B    = 3
} pedd_channel_t;

/* Analog Comparator, Timer1, GPIO를 초기화한다. 전원 투입 후 1회만 호출. */
void pedd_init(void);

/*
 * 지정한 발광 채널을 점등한 상태에서 검출 LED의 충전-방전 시간을 1회 측정한다.
 * 측정이 끝나면 발광 LED는 자동으로 소등된다.
 */
pedd_result_t pedd_measure(pedd_channel_t ch);

/* 틱 단위 값을 마이크로초로 변환 (1틱 = 0.5us) */
static inline uint32_t pedd_ticks_to_us(uint32_t ticks) {
  return ticks / 2;
}

#endif /* PEDD_H */
