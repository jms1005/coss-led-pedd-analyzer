/*
 * 02_phase1 — Phase 1 단일 채널 개념 증명 펌웨어
 *
 * 목적 (계획서 4.1절)
 *   LED 한 쌍(발광 1 + 검출 1)만으로 방전 시간 측정이 재현 가능한지,
 *   그리고 시료 간 차이를 반영하는지 확인한다.
 *   아울러 Overflow Counter와 Timeout 처리가 정상 동작하는지 검증한다.
 *
 * 동작
 *   한 사이클마다 다음 두 가지를 연속 측정하고 UART로 1행씩 출력한다.
 *     DARK — 발광 LED 전체 소등. 환경광 + 암전류 성분.
 *     R    — 발광 LED 점등. 시료를 투과한 광량.
 *   두 값의 차이가 계획서 3.8.1절의 "발광 ON/OFF 차분" 보정 재료가 된다.
 *
 * 배선 — Arduino Uno 기준 (괄호 안은 보드에 인쇄된 핀 번호, 계획서 6.1절)
 *   검출 LED : 캐소드 -> PD7 (D7),  애노드 -> GND
 *              ※ 극성을 반대로 연결하면 순방향이 되어 측정이 성립하지 않는다.
 *              ※ 검출 LED는 반드시 적색을 쓴다. 청색·녹색은 자기 파장보다
 *                 긴 빛에 반응하지 못해 Red 채널이 TIMEOUT이 된다.
 *   발광 LED : PB0 (D8) -> 저항(220~1k) -> LED 애노드, LED 캐소드 -> GND
 *   UART     : 보드의 USB 케이블이 그대로 담당한다 (PD0/PD1)
 *
 * PC 측 수신 설정 : 38400 bps, 8N1
 *   출력 형식은 CSV이므로 터미널 프로그램의 로그를 그대로 파일로 저장한 뒤
 *   tools/analyze.py 에 넣으면 된다.
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>

#include "pedd.h"
#include "uart.h"

/* 한 측정 사이클 사이의 간격 */
#define CYCLE_INTERVAL_MS 1000

/* 측정 결과 1건을 CSV 한 행으로 출력한다 */
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

  /* 전역 인터럽트 허용 — Timer1 캡처/오버플로우 ISR이 동작하려면 필요하다 */
  sei();

  /* 분석 스크립트가 인식하는 CSV 헤더 */
  uart_newline();
  uart_puts("# PEDD Phase 1 log / 1 tick = 500ns");
  uart_newline();
  uart_puts("seq,ch,status,ticks,us,ovf");
  uart_newline();

  while (1) {
    pedd_result_t dark, red;

    /* 환경광 + 암전류 성분 (계획서 6.3절 3항) */
    dark = pedd_measure(PEDD_CH_DARK);
    log_result(seq, "DARK", dark);

    /* 시료 투과 측정 */
    red = pedd_measure(PEDD_CH_R);
    log_result(seq, "R", red);

    seq++;
    _delay_ms(CYCLE_INTERVAL_MS);
  }

  return 0;  /* 도달하지 않음 */
}
