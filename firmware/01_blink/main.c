/*
 * 01_blink — 툴체인 검증용 최소 프로그램
 *
 * 목적: Microchip Studio 빌드 + 보드 업로드가 정상 동작하는지 확인한다.
 *       (계획서 7장 "툴체인 검증" 단계의 통과 조건)
 *
 * 요강 대응: Arduino 라이브러리를 쓰지 않고 DDRB / PORTB 레지스터를
 *           직접 read/write 하여 핀을 제어한다. (운영설명 PDF 1-라)
 *
 * 배선: 필요 없다. 보드에 내장된 "L" LED가 PB5(디지털 13번)에
 *       연결되어 있으므로, USB 케이블만 꽂고 업로드하면 된다.
 */

#ifndef F_CPU
#define F_CPU 16000000UL  /* 외부 16MHz 크리스털 기준 */
#endif

#include <avr/io.h>
#include <util/delay.h>

/* 검증용 LED가 연결된 핀 */
#define LED_BIT PB5

int main(void) {
  /* DDRB: 데이터 방향 레지스터. 해당 비트를 1로 두면 출력 핀이 된다. */
  DDRB |= (1 << LED_BIT);

  while (1) {
    /* PORTB의 비트를 1로 → 핀 HIGH → LED 점등 */
    PORTB |= (1 << LED_BIT);
    _delay_ms(500);

    /* PORTB의 비트를 0으로 → 핀 LOW → LED 소등 */
    PORTB &= ~(1 << LED_BIT);
    _delay_ms(500);
  }

  return 0;  /* 도달하지 않음 */
}
