/* classify 모듈 단위 테스트. PC에서 실행한다. */

#include <stdio.h>
#include <stdlib.h>
#include "classify.h"

static int g_fail = 0;

static void check(int cond, const char *name) {
  if (cond) {
    printf("  PASS  %s\n", name);
  } else {
    printf("  FAIL  %s\n", name);
    g_fail++;
  }
}

/* 세 채널이 같으면 지문은 균등해야 한다 */
static void test_uniform(void) {
  fingerprint_t fp = classify_fingerprint(0, 1000, 1000, 1000);
  check(fp.status == CLASSIFY_OK, "균등 입력 - 상태 OK");
  check(fp.n[0] == fp.n[1] && fp.n[1] == fp.n[2], "균등 입력 - 세 채널 동일");
  check(fp.n[0] >= 330 && fp.n[0] <= 334, "균등 입력 - 각 채널 약 333");
}

/* 합은 항상 NORM_SUM 근처여야 한다 (절단 오차 허용) */
static void test_sum_normalized(void) {
  fingerprint_t fp = classify_fingerprint(0, 1204, 980, 1510);
  uint32_t s = (uint32_t)fp.n[0] + fp.n[1] + fp.n[2];
  check(fp.status == CLASSIFY_OK, "일반 입력 - 상태 OK");
  check(s >= 997 && s <= 1000, "일반 입력 - 합이 1000 근처");
}

/* 밝은 쪽(t가 작은 쪽)이 더 큰 성분을 가져야 한다 */
static void test_ordering(void) {
  fingerprint_t fp = classify_fingerprint(0, 980, 1204, 1510);
  check(fp.n[0] > fp.n[1] && fp.n[1] > fp.n[2], "t가 작을수록 성분이 큼");
}

/* 경계: 최소 t. 오버플로우 없이 정상 정규화되어야 한다 */
static void test_min_t(void) {
  fingerprint_t fp = classify_fingerprint(0, 1, 1, 1);
  uint32_t s = (uint32_t)fp.n[0] + fp.n[1] + fp.n[2];
  check(fp.status == CLASSIFY_OK, "t=1 - 상태 OK");
  check(s >= 997 && s <= 1000, "t=1 - 합이 1000 근처 (오버플로우 없음)");
}

/* 경계: 최대 t (TIMEOUT_OVF 61 x 65536) */
static void test_max_t(void) {
  fingerprint_t fp = classify_fingerprint(0, 3997696UL, 3997696UL, 3997696UL);
  check(fp.status == CLASSIFY_LOW_SIGNAL, "t=최대 - 신호 부족으로 판정");
}

/* 암전류 보정: DARK가 밝으면 각 채널 성분이 줄어야 한다 */
static void test_dark_correction(void) {
  fingerprint_t a = classify_fingerprint(0,      1000, 2000, 4000);
  fingerprint_t b = classify_fingerprint(100000, 1000, 2000, 4000);
  check(a.status == CLASSIFY_OK && b.status == CLASSIFY_OK, "암보정 - 둘 다 OK");
  check(a.n[0] != b.n[0], "암보정 - DARK 값이 지문을 바꿈");
}

/* DARK 타임아웃(0)은 오류가 아니라 보정량 0을 뜻한다 */
static void test_dark_timeout_ok(void) {
  fingerprint_t fp = classify_fingerprint(0, 1204, 980, 1510);
  check(fp.status == CLASSIFY_OK, "DARK=0 - 정상 처리");
}

/* 모든 채널이 타임아웃이면 신호 부족 */
static void test_all_timeout(void) {
  fingerprint_t fp = classify_fingerprint(0, 0, 0, 0);
  check(fp.status == CLASSIFY_LOW_SIGNAL, "전 채널 타임아웃 - 신호 부족");
  check(fp.n[0] == 0 && fp.n[1] == 0 && fp.n[2] == 0, "전 채널 타임아웃 - 지문 0");
}

/* 정확히 일치하는 중심점은 거리 0 */
static void test_match_exact(void) {
  static const uint16_t c[3][3] = { {333,333,333}, {600,200,200}, {200,200,600} };
  fingerprint_t fp = classify_fingerprint(0, 1000, 1000, 1000);
  classify_result_t r = classify_match(&fp, c, 1600);
  check(r.cls == 0, "정확 일치 - 클래스 0");
  check(r.d2 <= 12, "정확 일치 - 거리 거의 0");
}

/* 임계값을 넘으면 미상 */
static void test_match_unknown(void) {
  static const uint16_t c[3][3] = { {900,50,50}, {50,900,50}, {50,50,900} };
  fingerprint_t fp = classify_fingerprint(0, 1000, 1000, 1000);
  classify_result_t r = classify_match(&fp, c, 1600);
  check(r.cls == -1, "임계값 초과 - 미상");
  check(r.d2 > 1600, "임계값 초과 - d2가 임계값보다 큼");
}

/* 신호 부족 지문은 무조건 미상 */
static void test_match_low_signal(void) {
  static const uint16_t c[3][3] = { {333,333,333}, {600,200,200}, {200,200,600} };
  fingerprint_t fp = classify_fingerprint(0, 0, 0, 0);
  classify_result_t r = classify_match(&fp, c, 1600);
  check(r.cls == -1, "신호 부족 - 미상");
}

static void test_isqrt(void) {
  check(classify_isqrt(0) == 0, "isqrt(0)=0");
  check(classify_isqrt(1) == 1, "isqrt(1)=1");
  check(classify_isqrt(1600) == 40, "isqrt(1600)=40");
  check(classify_isqrt(1601) == 40, "isqrt(1601)=40 (내림)");
  check(classify_isqrt(3000000UL) == 1732, "isqrt(3000000)=1732");
}

int main(void) {
  printf("== classify 단위 테스트 ==\n");
  test_uniform();
  test_sum_normalized();
  test_ordering();
  test_min_t();
  test_max_t();
  test_dark_correction();
  test_dark_timeout_ok();
  test_all_timeout();
  test_match_exact();
  test_match_unknown();
  test_match_low_signal();
  test_isqrt();
  printf("== 실패 %d건 ==\n", g_fail);
  return g_fail == 0 ? 0 : 1;
}
