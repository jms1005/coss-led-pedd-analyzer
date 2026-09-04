/*
 * store 모듈 단위 테스트. PC에서 실행한다.
 *
 * 브링업 5단계의 "전원을 껐다 켜도 READY 가 뜨는가" 가 이 모듈에
 * 걸려 있다. EEPROM 을 배열로 흉내내어 저장-복원 왕복과 손상 거부를
 * 실물 없이 확인한다.
 */

#include <stdio.h>
#include <string.h>

#include "avr/io.h"
#include "store.h"

static int g_fail = 0;

static void check(int cond, const char *name) {
  if (cond) {
    printf("  PASS  %s\n", name);
  } else {
    printf("  FAIL  %s\n", name);
    g_fail++;
  }
}

static void fill(uint16_t c[CLASSIFY_CLASSES][CLASSIFY_CHANNELS], uint16_t base) {
  uint8_t i, k;
  for (i = 0; i < CLASSIFY_CLASSES; i++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      c[i][k] = (uint16_t)(base + i * 100 + k);
    }
  }
}

static int same(uint16_t a[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                uint16_t b[CLASSIFY_CLASSES][CLASSIFY_CHANNELS]) {
  uint8_t i, k;
  for (i = 0; i < CLASSIFY_CLASSES; i++) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      if (a[i][k] != b[i][k]) {
        return 0;
      }
    }
  }
  return 1;
}

/* 저장한 뒤 배열을 직접 볼 수 있도록 대기 중인 쓰기를 반영한다 */
static void save_and_flush(uint16_t c[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                           uint32_t th) {
  store_save((const uint16_t (*)[CLASSIFY_CHANNELS])c, th);
  fake_ee_flush();
}

/* 공장 출하 상태(전부 0xFF)는 학습 안 됨으로 걸러져야 한다 */
static void test_blank(void) {
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  check(store_load(out, &th) == 0, "공장 출하(0xFF) - 학습 안 됨으로 거부");
}

/* 저장한 값이 그대로 돌아와야 한다 */
static void test_roundtrip(void) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 1600);
  memset(out, 0, sizeof(out));
  check(store_load(out, &th) == 1, "왕복 - 복원 성공");
  check(same(in, out), "왕복 - 중심점 9개가 모두 일치");
  check(th == 1600, "왕복 - 임계값 일치");
}

/* 쓰는 범위가 STORE_SIZE 를 넘지 않아야 한다 */
static void test_footprint(void) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t a;
  int clean = 1;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 1600);
  for (a = STORE_SIZE; a < 64; a++) {
    if (fake_eeprom[a] != 0xFF) {
      clean = 0;
    }
  }
  check(clean, "사용 범위 - STORE_SIZE(26) 밖을 건드리지 않음");
}

/* 각 검사 항목이 실제로 걸러내는지 — 한 바이트씩 망가뜨려 본다 */
static void corrupt_case(uint16_t addr, const char *name) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 1600);
  fake_eeprom[addr] = (uint8_t)(fake_eeprom[addr] ^ 0xFF);
  check(store_load(out, &th) == 0, name);
}

/*
 * 위의 필드별 검사는 각 필드의 첫 바이트만 뒤집는다. 그것만으로는
 * 체크섬이 훑는 범위가 한 바이트 모자라도 통과해버린다 (변이 테스트로
 * 확인했다). 그래서 저장 영역 전체를 한 바이트씩 훑는다.
 */
static void test_corruption_every_byte(void) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th;
  uint16_t addr;
  int escaped = -1;

  for (addr = 0; addr < STORE_SIZE; addr++) {
    fake_ee_reset();
    fill(in, 300);
    save_and_flush(in, 1600);
    fake_eeprom[addr] = (uint8_t)(fake_eeprom[addr] ^ 0xFF);
    th = 0;
    if (store_load(out, &th) != 0 && escaped < 0) {
      escaped = (int)addr;
    }
  }
  if (escaped >= 0) {
    printf("        (거르지 못한 주소: %d)\n", escaped);
  }
  check(escaped < 0, "손상 - 26바이트 중 어느 하나를 뒤집어도 모두 거부");
}

/*
 * 체크섬까지 맞는데 형식만 다른 기록. 손상이 아니라 "옛 펌웨어가
 * 정상적으로 저장해 둔 데이터" 다. 브링업 중 펌웨어를 여러 번 다시
 * 올리므로 실제로 생길 수 있고, 이때 그냥 읽어들이면 엉뚱한 중심점으로
 * 조용히 오분류한다. 매직·버전·클래스 수 검사가 막아야 하는 경우다.
 */
static void reseal(void) {
  uint16_t sum = 0;
  uint16_t a;
  for (a = 0; a < STORE_ADDR_CHECKSUM; a++) {
    sum = (uint16_t)(sum + fake_eeprom[a]);
  }
  fake_eeprom[STORE_ADDR_CHECKSUM]     = (uint8_t)(sum & 0xFF);
  fake_eeprom[STORE_ADDR_CHECKSUM + 1] = (uint8_t)(sum >> 8);
}

static void incompatible_case(uint16_t addr, uint8_t value, const char *name) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 1600);
  fake_eeprom[addr] = value;
  reseal();
  check(store_load(out, &th) == 0, name);
}

static void test_incompatible(void) {
  incompatible_case(STORE_ADDR_MAGIC, 0x34,
                    "형식 불일치 - 매직이 다르면 거부 (체크섬은 맞음)");
  incompatible_case(STORE_ADDR_VERSION, (uint8_t)(STORE_VERSION + 1),
                    "형식 불일치 - 버전이 올라가면 거부 (체크섬은 맞음)");
  incompatible_case(STORE_ADDR_COUNT, (uint8_t)(CLASSIFY_CLASSES + 1),
                    "형식 불일치 - 클래스 수가 다르면 거부 (체크섬은 맞음)");
}

static void test_corruption(void) {
  corrupt_case(STORE_ADDR_MAGIC,     "손상 - 매직이 깨지면 거부");
  corrupt_case(STORE_ADDR_VERSION,   "손상 - 버전이 다르면 거부");
  corrupt_case(STORE_ADDR_COUNT,     "손상 - 클래스 수가 다르면 거부");
  corrupt_case(STORE_ADDR_CENTROIDS, "손상 - 중심점이 바뀌면 체크섬이 거부");
  corrupt_case(STORE_ADDR_THRESHOLD, "손상 - 임계값이 바뀌면 체크섬이 거부");
  corrupt_case(STORE_ADDR_CHECKSUM,  "손상 - 체크섬 자체가 깨지면 거부");
}

/* 지우면 학습 안 됨 상태로 돌아가야 한다 */
static void test_erase(void) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 1600);
  check(store_load(out, &th) == 1, "지우기 - 지우기 전에는 복원됨");
  store_erase();
  fake_ee_flush();
  check(store_load(out, &th) == 0, "지우기 - 지운 뒤에는 거부");
}

/* 두 번 저장하면 나중 값이 남아야 한다 */
static void test_overwrite(void) {
  uint16_t a[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t b[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(a, 300);
  save_and_flush(a, 1600);
  fill(b, 700);
  save_and_flush(b, 2500);
  check(store_load(out, &th) == 1, "재학습 - 복원 성공");
  check(same(b, out), "재학습 - 나중에 저장한 값이 남음");
  check(th == 2500, "재학습 - 임계값도 갱신됨");
}

/*
 * 현재 구현의 확인: 임계값은 32비트로 받지만 16비트로 저장한다.
 *
 * store_save 의 인자는 uint32_t 인데 ee_write16 으로 내려가면서
 * 하위 16비트만 남는다. THRESHOLD_D2 가 1600 상수인 지금은 문제가
 * 없지만, 실험 뒤 임계를 65535 이상으로 올리면 경고 없이 값이 바뀐다.
 * 정규화 지문(합 1000)에서 거리 256 이면 d2 가 65536 이다.
 */
static void test_threshold_truncation(void) {
  uint16_t in[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint16_t out[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
  uint32_t th = 0;
  fake_ee_reset();
  fill(in, 300);
  save_and_flush(in, 70000u);
  check(store_load(out, &th) == 1, "임계값 절단 - 복원 자체는 성공");
  check(th == (70000u & 0xFFFFu), "임계값 절단 - 65535 초과분이 잘린다 (현재 동작)");
}

int main(void) {
  printf("== store 단위 테스트 ==\n");
  test_blank();
  test_roundtrip();
  test_footprint();
  test_corruption();
  test_corruption_every_byte();
  test_incompatible();
  test_erase();
  test_overwrite();
  test_threshold_truncation();
  printf("== 실패 %d건 ==\n", g_fail);
  return g_fail ? 1 : 0;
}
