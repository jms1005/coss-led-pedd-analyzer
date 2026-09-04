/*
 * 가짜 avr/io.h — PC 에서 펌웨어 모듈을 그대로 컴파일하기 위한 것.
 *
 * 펌웨어는 한 줄도 고치지 않는다. 이 폴더를 -I 경로 맨 앞에 두면
 * #include <avr/io.h> 가 진짜 대신 이 파일을 집는다.
 *
 * EEPROM 은 레지스터 동작까지 흉내낸다. EECR 과 EEDR 을 함수 호출로
 * 바꿔 접근 순간에 다음을 처리한다.
 *
 *   EERE 가 서 있으면  -> 배열에서 EEDR 로 읽어온다
 *   EEPE 가 서 있으면  -> EEDR 을 배열에 쓴다 (다음 접근 때 반영)
 *
 * 실제 하드웨어도 쓰기가 즉시 끝나지 않고 EEPE 가 내려갈 때까지
 * 걸리므로, "다음 접근에서 반영" 은 실물 동작과 어긋나지 않는다.
 * store.c 가 모든 접근 앞에 while (EECR & (1 << EEPE)) 대기를 두기
 * 때문에 순서도 그대로 지켜진다.
 */

#ifndef FAKE_AVR_IO_H
#define FAKE_AVR_IO_H

#include <stdint.h>

/* ---- 포트 (버튼용) ---- */
extern uint8_t fake_ddrd;
extern uint8_t fake_portd;
extern uint8_t fake_pind;

#define DDRD  fake_ddrd
#define PORTD fake_portd
#define PIND  fake_pind
#define PD2   2

/* ---- EEPROM ---- */
#define FAKE_EEPROM_SIZE 1024
extern uint8_t fake_eeprom[FAKE_EEPROM_SIZE];

uint8_t *fake_eecr_ref(void);
uint8_t *fake_eedr_ref(void);

#define EECR  (*fake_eecr_ref())
#define EEDR  (*fake_eedr_ref())

extern uint8_t fake_eearh;
extern uint8_t fake_eearl;

#define EEARH fake_eearh
#define EEARL fake_eearl

/* ATmega328P 의 실제 비트 위치 */
#define EERE  0
#define EEPE  1
#define EEMPE 2

/* 테스트용 보조 */
void fake_ee_reset(void);        /* 공장 출하 상태(0xFF)로 되돌린다 */
void fake_ee_flush(void);        /* 대기 중인 쓰기를 지금 반영한다 */

#endif /* FAKE_AVR_IO_H */
