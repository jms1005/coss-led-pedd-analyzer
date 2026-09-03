/*
 * 03_phase2 — Phase 2 RGB 다파장 확장 펌웨어
 *
 * 목적 (계획서 4.2절)
 *   파장을 추가할수록 실제로 판별에 유의미한 정보가 증가하는지 검증하고,
 *   최종 채널 구성을 실험적으로 결정한다.
 *
 * 동작
 *   한 사이클마다 DARK → R → G → B 순으로 측정하고, 각각을 CSV 한 행으로
 *   출력한다. 같은 seq 번호를 가진 네 행이 하나의 측정 세트다.
 *   tools/analyze.py 가 seq로 묶어 광학 지문 벡터 [R, G, B] 를 재구성한다.
 *
 *   한 번에 하나의 LED만 점등하므로 채널 간 광학적 간섭은 발생하지 않는다.
 *   (계획서 3.1절)
 *
 * 배선 — Arduino Uno 기준 (괄호 안은 보드에 인쇄된 핀 번호)
 *   발광 Red   : PB0 (D8)  → 저항 → LED 애노드, 캐소드 → GND
 *   발광 Green : PB1 (D9)  → 저항 → LED 애노드, 캐소드 → GND
 *   발광 Blue  : PB2 (D10) → 저항 → LED 애노드, 캐소드 → GND
 *   검출 LED   : 캐소드 → PD7 (D7),  애노드 → GND
 *                ※ 검출 LED는 반드시 적색. 청색·녹색을 쓰면 Red 채널에서
 *                   광전류가 거의 흐르지 않아 TIMEOUT이 된다.
 *   UART       : 보드의 USB 케이블이 그대로 담당 (PD0/PD1)
 *
 * PC 측 수신 설정 : 38400 bps, 8N1
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>

#include "pedd.h"
#include "uart.h"

/* 한 측정 세트 사이의 간격 */
#define CYCLE_INTERVAL_MS 1000

/* 스캔 순서 — 계획서 1.4절 데모 시나리오와 동일하게 R → G → B */
static const pedd_channel_t SCAN_ORDER[] = {
  PEDD_CH_DARK,
  PEDD_CH_R,
  PEDD_CH_G,
  PEDD_CH_B
};

static const char *const SCAN_NAME[] = {
  "DARK",
  "R",
  "G",
  "B"
};

#define SCAN_COUNT (sizeof(SCAN_ORDER) / sizeof(SCAN_ORDER[0]))

static void log_result(uint32_t seq, const char *ch_name, pedd_result_t r) {
  uart_put_u32(seq);
  uart_putc(',');
  uart_puts(ch_name);
  uart_putc(',');
  uart_puts(r.status == PEDD_OK ? "OK" : "TIMEOUT");
  uart_putc(',');
  uart_put_u32(r.ticks);
  uart_putc(',');
  uart_put_u32(pedd_ticks_to_us(r.ticks));
  uart_putc(',');
  uart_put_u32(r.overflows);
  uart_newline();
}

int main(void) {
  uint32_t seq = 0;

  uart_init();
  pedd_init();
  sei();

  uart_newline();
  uart_puts("# PEDD Phase 2 log / 1 tick = 500ns / scan: DARK,R,G,B");
  uart_newline();
  uart_puts("seq,ch,status,ticks,us,ovf");
  uart_newline();

  while (1) {
    uint8_t i;

    /* 한 사이클 = 광학 지문 벡터 1개분 */
    for (i = 0; i < SCAN_COUNT; i++) {
      pedd_result_t r = pedd_measure(SCAN_ORDER[i]);
      log_result(seq, SCAN_NAME[i], r);
    }

    seq++;
    _delay_ms(CYCLE_INTERVAL_MS);
  }

  return 0;  /* 도달하지 않음 */
}
