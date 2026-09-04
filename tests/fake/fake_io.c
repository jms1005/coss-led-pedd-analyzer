/* 가짜 레지스터의 실체. tests/fake/avr/io.h 참조. */

#include <string.h>

#include "avr/io.h"

uint8_t fake_ddrd  = 0;
uint8_t fake_portd = 0;
uint8_t fake_pind  = 0xFF;   /* 풀업 상태 = 버튼 안 눌림 */

uint8_t fake_eeprom[FAKE_EEPROM_SIZE];
uint8_t fake_eearh = 0;
uint8_t fake_eearl = 0;

static uint8_t s_eecr = 0;
static uint8_t s_eedr = 0;

static uint16_t cur_addr(void) {
  return (uint16_t)(((uint16_t)fake_eearh << 8) | fake_eearl);
}

uint8_t *fake_eecr_ref(void) {
  /* 대기 중인 쓰기를 반영한다. 주소는 EEPE 를 세우기 전에 정해지고
     그 뒤 바뀌지 않으므로 지금 읽어도 같은 값이다. */
  if (s_eecr & (1 << EEPE)) {
    uint16_t a = cur_addr();
    if (a < FAKE_EEPROM_SIZE) {
      fake_eeprom[a] = s_eedr;
    }
    s_eecr &= (uint8_t)~(1 << EEPE);
  }
  return &s_eecr;
}

uint8_t *fake_eedr_ref(void) {
  if (s_eecr & (1 << EERE)) {
    uint16_t a = cur_addr();
    s_eedr = (a < FAKE_EEPROM_SIZE) ? fake_eeprom[a] : 0xFF;
    s_eecr &= (uint8_t)~(1 << EERE);
  }
  return &s_eedr;
}

void fake_ee_reset(void) {
  memset(fake_eeprom, 0xFF, sizeof(fake_eeprom));
  s_eecr = 0;
  s_eedr = 0;
  fake_eearh = 0;
  fake_eearl = 0;
}

void fake_ee_flush(void) {
  (void)fake_eecr_ref();
}
