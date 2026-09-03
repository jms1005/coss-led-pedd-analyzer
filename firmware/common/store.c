/*
 * store.c — EEPROM 접근 (레지스터 직접 제어)
 */

#include <avr/io.h>
#include <util/atomic.h>

#include "store.h"

static uint8_t ee_read(uint16_t addr) {
  /* 이전 쓰기가 끝날 때까지 대기 */
  while (EECR & (1 << EEPE)) {
  }
  EEARH = (uint8_t)(addr >> 8);
  EEARL = (uint8_t)(addr & 0xFF);
  EECR |= (1 << EERE);
  return EEDR;
}

static void ee_write(uint16_t addr, uint8_t value) {
  while (EECR & (1 << EEPE)) {
  }
  EEARH = (uint8_t)(addr >> 8);
  EEARL = (uint8_t)(addr & 0xFF);
  EEDR  = value;
  /*
   * EEMPE 를 세운 뒤 4클럭 안에 EEPE 를 세워야 한다.
   * 인터럽트가 끼어들면 이 창을 놓치므로 원자 구간으로 감싼다.
   */
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    EECR |= (1 << EEMPE);
    EECR |= (1 << EEPE);
  }
}

static uint16_t ee_read16(uint16_t addr) {
  return (uint16_t)((uint16_t)ee_read(addr) | ((uint16_t)ee_read(addr + 1) << 8));
}

static void ee_write16(uint16_t addr, uint16_t value) {
  ee_write(addr,     (uint8_t)(value & 0xFF));
  ee_write((uint16_t)(addr + 1), (uint8_t)(value >> 8));
}

/* 앞 24바이트의 단순 합. 상위 비트는 버린다. */
static uint16_t checksum_stored(void) {
  uint16_t sum = 0;
  uint16_t a;
  for (a = 0; a < STORE_ADDR_CHECKSUM; a++) {
    sum = (uint16_t)(sum + ee_read(a));
  }
  return sum;
}

uint8_t store_load(uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                   uint32_t *threshold_d2) {
  uint8_t c, k;
  uint16_t addr;

  if (ee_read16(STORE_ADDR_MAGIC) != STORE_MAGIC) {
    return 0;
  }
  if (ee_read(STORE_ADDR_VERSION) != STORE_VERSION) {
    return 0;
  }
  if (ee_read(STORE_ADDR_COUNT) != CLASSIFY_CLASSES) {
    return 0;
  }
  if (ee_read16(STORE_ADDR_CHECKSUM) != checksum_stored()) {
    return 0;
  }

  addr = STORE_ADDR_CENTROIDS;
  for (c = 0; c < CLASSIFY_CLASSES; c++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      centroids[c][k] = ee_read16(addr);
      addr = (uint16_t)(addr + 2);
    }
  }
  *threshold_d2 = ee_read16(STORE_ADDR_THRESHOLD);
  return 1;
}

void store_save(const uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                uint32_t threshold_d2) {
  uint8_t c, k;
  uint16_t addr;

  ee_write16(STORE_ADDR_MAGIC, STORE_MAGIC);
  ee_write(STORE_ADDR_VERSION, STORE_VERSION);
  ee_write(STORE_ADDR_COUNT,   CLASSIFY_CLASSES);

  addr = STORE_ADDR_CENTROIDS;
  for (c = 0; c < CLASSIFY_CLASSES; c++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      ee_write16(addr, centroids[c][k]);
      addr = (uint16_t)(addr + 2);
    }
  }
  ee_write16(STORE_ADDR_THRESHOLD, (uint16_t)threshold_d2);

  /* 체크섬은 나머지를 모두 기록한 뒤 마지막에 쓴다. */
  ee_write16(STORE_ADDR_CHECKSUM, checksum_stored());
}

void store_erase(void) {
  ee_write16(STORE_ADDR_MAGIC, 0xFFFF);
}
