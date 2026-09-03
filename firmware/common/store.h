/*
 * store.h — 학습된 중심점을 EEPROM에 보관한다.
 *
 * avr-libc 의 eeprom_* 함수 대신 EECR/EEDR/EEARH/EEARL 레지스터를 직접
 * 제어한다. 요강의 "레지스터 직접 read/write" 취지에 맞춘다.
 */

#ifndef STORE_H
#define STORE_H

#include <stdint.h>
#include "classify.h"

/* EEPROM 배치 (스펙 8절). 총 26바이트 */
#define STORE_ADDR_MAGIC      0
#define STORE_ADDR_VERSION    2
#define STORE_ADDR_COUNT      3
#define STORE_ADDR_CENTROIDS  4
#define STORE_ADDR_THRESHOLD  22
#define STORE_ADDR_CHECKSUM   24
#define STORE_SIZE            26

#define STORE_MAGIC    0x5044u
#define STORE_VERSION  1

/*
 * 저장된 중심점을 읽는다. 매직·버전·클래스 수·체크섬이 모두 맞아야 1을
 * 반환한다. 공장 출하 EEPROM은 전부 0xFF 라 자연스럽게 무효로 걸러진다.
 * 0을 반환하면 인자는 건드리지 않는다.
 */
uint8_t store_load(uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                   uint32_t *threshold_d2);

/* 중심점 전체를 한 번에 기록한다. 학습이 끝난 뒤에만 호출한다. */
void store_save(const uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                uint32_t threshold_d2);

/* 매직을 지워 "학습 안 됨" 상태로 되돌린다. */
void store_erase(void);

#endif /* STORE_H */
