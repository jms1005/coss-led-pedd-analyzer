/*
 * store.c — EEPROM 접근 (레지스터 직접 제어)
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * EEPROM 은 칩 안에 있는 작은 저장 공간으로, 전원을 꺼도 내용이 남는다.
 * (ATmega328P 는 1KB) SRAM 변수는 전원을 끄면 사라지므로, 학습한 중심점을
 * 다음에도 쓰려면 여기에 넣어야 한다. "한 번 배우면 계속 기억한다" 는
 * 동작이 이 파일 덕분이다.
 *
 * 문제는 EEPROM 이 처음에는 전부 0xFF 인 빈 상태이고, 쓰다가 전원이 끊기면
 * 반만 써진 쓰레기가 남을 수도 있다는 점이다. 그걸 그대로 읽어 학습
 * 데이터로 믿으면 엉뚱한 판정을 한다. 그래서 세 겹으로 확인한다.
 *
 *   매직값    우리가 쓴 데이터가 맞는가 (빈 EEPROM 과 구별)
 *   버전      지금 코드가 아는 형식인가 (예전 형식을 잘못 읽지 않도록)
 *   체크섬    중간에 깨지지 않았는가 (앞부분 바이트를 모두 더한 값)
 *
 * 셋 중 하나라도 어긋나면 store_load() 가 0 을 반환하고, main.c 는
 * 화면에 NOT TRAINED 를 띄운다. 애매하면 안 배운 셈 치는 쪽이 안전하다.
 *
 * EEPROM 쓰기는 한 바이트에 3.3ms 로 느리다. 그래서 매 측정마다가 아니라
 * 학습을 마칠 때 한 번만 저장한다. 수명도 10만 회로 유한하다.
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
  /*
   * 임계값은 EEPROM 배치(스펙 8절)상 2바이트다. 그런데 d2 는 uint32 이고
   * 이론상 최대 3,000,000 까지 나온다(1000^2 x 3채널). 그대로 잘라 쓰면
   * 예를 들어 70000 이 4464 로 뒤집혀 "전부 UNKNOWN" 이 되는데, 원인이
   * 저장 단계에 있어 추적이 아주 어렵다.
   * 넘치면 상한에 붙여 둔다. 65535 는 거리로 약 256 이고, 지문 합이 1000
   * 인 척도에서 사실상 "무엇이든 받아들임" 이라 의도와 어긋나지 않는다.
   */
  ee_write16(STORE_ADDR_THRESHOLD,
             (threshold_d2 > 0xFFFFUL) ? 0xFFFFu : (uint16_t)threshold_d2);

  /*
   * 체크섬은 반드시 마지막에 쓴다.
   * 쓰는 도중 전원이 끊기면 앞부분만 저장된 상태로 남는데, 그때 체크섬이
   * 아직 안 쓰였으므로 다음 부팅에서 검사가 실패한다. 즉 "반쯤 저장된
   * 데이터"를 유효한 것으로 착각하는 일이 생기지 않는다.
   * 순서를 바꾸면 이 보호가 사라진다.
   */
  ee_write16(STORE_ADDR_CHECKSUM, checksum_stored());
}

/*
 * 학습 데이터를 무효화한다. 24바이트를 다 지우지 않고 매직값만 망가뜨린다.
 * store_load() 가 매직값부터 보므로 이것만으로 "안 배운 상태"가 되고,
 * 느린 EEPROM 쓰기를 2바이트로 끝낼 수 있다.
 */
void store_erase(void) {
  ee_write16(STORE_ADDR_MAGIC, 0xFFFF);
}
