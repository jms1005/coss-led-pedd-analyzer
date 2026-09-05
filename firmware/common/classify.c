/*
 * classify.c — 광학 지문 계산과 최근접 중심점 판정
 *
 * 설계 근거는 docs/superpowers/specs/2026-09-03-phase4-design.md 7절.
 * 전 구간 32비트 정수. float 를 쓰지 않으므로 소프트웨어 부동소수점
 * 라이브러리(약 1.5~3KB Flash)가 링크되지 않는다.
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * 입력은 pedd.c 가 잰 방전 시간 4개(DARK, R, G, B)뿐이다. 이 숫자만 가지고
 * "어떤 액체인가"를 답해야 한다. 세 단계를 거친다.
 *
 *   1. 시간 -> 밝기        시간이 짧을수록 빛이 세다. 그래서 역수를 쓴다.
 *   2. 밝기 -> 지문        어두운 방 몫(DARK)을 빼고, 세 채널의 비율만 남긴다.
 *   3. 지문 -> 이름        미리 배워둔 지문 중 가장 가까운 것을 고른다.
 *
 * 2번에서 "비율만" 남기는 것이 핵심이다. LED 를 큐벳에 조금 가깝게 놓으면
 * 세 채널이 모두 밝아지지만, 액체가 같다면 채널 사이의 비율은 그대로다.
 * 절대값 대신 비율을 쓰면 이런 흔들림에 판정이 흔들리지 않는다.
 *
 * 이 파일이 <avr/io.h> 를 포함하지 않는 이유는 classify.h 에 적어 두었다.
 * (PC 에서 그대로 컴파일해 단위 테스트하기 위함. tests/test_classify.c)
 */

#include "classify.h"

/*
 * 1단계 — 방전 시간을 컨덕턴스(밝기에 비례하는 값)로 바꾼다.
 *
 * 빛이 셀수록 전하가 빨리 빠져 t 가 작아진다. 즉 t 는 밝기에 반비례하므로
 * 역수를 취하면 밝기에 비례하는 값이 된다. 정수만 쓰기 위해 1 을 나누는
 * 대신 큰 상수 K(=1e9)를 나눈다. 이렇게 하면 소수점 없이 유효 자릿수를
 * 확보할 수 있다.
 *
 * t == 0 은 타임아웃이며 "빛이 오지 않았다" = G 0 으로 본다.
 * t 최소값 1일 때 G = 1e9 이므로 세 채널 합의 최대는 3e9 < 4.29e9 (uint32 상한).
 */
static uint32_t conductance(uint32_t t) {
  if (t == 0) {
    return 0;
  }
  return CLASSIFY_K / t;
}

fingerprint_t classify_fingerprint(uint32_t t_dark, uint32_t t_r,
                                   uint32_t t_g, uint32_t t_b) {
  fingerprint_t fp;
  uint32_t t_ch[CLASSIFY_CHANNELS];
  uint32_t i[CLASSIFY_CHANNELS];
  uint32_t g_dark;
  uint32_t sum = 0;
  uint8_t k;

  t_ch[0] = t_r;
  t_ch[1] = t_g;
  t_ch[2] = t_b;

  g_dark = conductance(t_dark);

  /*
   * 2단계 — 암전류 보정.
   *
   * DARK 는 발광 LED 를 모두 끄고 잰 값이다. 그런데도 0 이 아닌 이유는,
   * 빛이 전혀 없어도 반도체 안에서 전하가 아주 조금씩 새기 때문이다.
   * 이것을 암전류라고 한다. 세 채널 모두 이 몫을 똑같이 깔고 있으므로
   * 빼 주어야 순수하게 "LED 빛 때문에 생긴 양"만 남는다.
   *
   * 부호 없는 정수라 빼서 음수가 되면 아주 큰 값으로 뒤집힌다.
   * 그래서 크기를 먼저 비교해 0 으로 눌러 둔다.
   */
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    uint32_t g = conductance(t_ch[k]);
    i[k] = (g > g_dark) ? (g - g_dark) : 0;
    sum += i[k];
  }

  /*
   * 보정하고 나니 남은 신호가 거의 없다 = 광 경로가 막혔거나 LED 극성이
   * 반대다. 이 상태로 정규화하면 의미 없는 값이 나오므로 여기서 끊는다.
   * 호출한 쪽(main.c)은 이 status 를 보고 화면에 LOW SIGNAL 을 띄운다.
   */
  if (sum < CLASSIFY_MIN_SIGNAL) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      fp.n[k] = 0;
    }
    fp.status = CLASSIFY_LOW_SIGNAL;
    return fp;
  }

  /*
   * 3단계 — 정규화 준비. 아래에서 i[k] * 1000 을 계산하는데, i[k] 가 크면
   * 이 곱셈이 32비트를 넘쳐 엉뚱한 값이 된다. 그래서 미리 줄여 둔다.
   *
   * 우측 시프트 1회는 2로 나누는 것과 같다. 세 채널을 "함께" 줄이므로
   * 채널 간 비율(= 지문)은 그대로 보존된다. 우리가 쓰려는 것은 비율뿐이니
   * 절대 크기가 작아지는 것은 상관없다.
   *
   * 시프트 후 sum <= 4e6, i[k] <= sum 이므로 i[k]*1000 <= 4.0e9 < 4.29e9.
   */
  while (sum > CLASSIFY_SHIFT_LIMIT) {
    sum = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      i[k] >>= 1;
      sum += i[k];
    }
  }

  /* 시프트로 sum이 0이 되는 일은 없지만 0 나누기를 원천 차단한다. */
  if (sum == 0) {
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      fp.n[k] = 0;
    }
    fp.status = CLASSIFY_LOW_SIGNAL;
    return fp;
  }

  /*
   * 정규화. 세 채널의 합이 항상 1000 이 되도록 비율로 고쳐 쓴다.
   * 예를 들어 (800, 200, 200) 과 (400, 100, 100) 은 밝기는 두 배 차이지만
   * 정규화하면 둘 다 (666, 166, 166) 이 되어 같은 지문으로 취급된다.
   * 이것이 이 파일 첫머리에서 말한 "비율만 남긴다" 의 실제 계산이다.
   */
  for (k = 0; k < CLASSIFY_CHANNELS; k++) {
    fp.n[k] = (uint16_t)((i[k] * CLASSIFY_NORM_SUM) / sum);
  }
  fp.status = CLASSIFY_OK;
  return fp;
}

/*
 * 4단계 — 판정. 지문 3개짜리 숫자 묶음을 "3차원 공간의 점 하나"로 본다.
 *
 * 학습 때 저장해 둔 액체별 점(중심점, centroid)이 3개 있다. 지금 잰 점이
 * 그중 어느 것과 가장 가까운지 재서 그 이름을 답으로 내놓는다. 이것이
 * "최근접 중심점(nearest centroid)" 방식이다.
 *
 * 거리는 피타고라스처럼 각 축의 차이를 제곱해 더한다. 다만 제곱근은
 * 씌우지 않는다. 크기 비교만 할 것이라면 제곱근을 씌우든 안 씌우든 순서가
 * 같기 때문이다. 제곱근 계산을 통째로 아낄 수 있다.
 *
 * 가장 가까운 점이라도 너무 멀면(threshold_d2 초과) 셋 중 무엇도 아니라고
 * 보고 -1(미상)을 돌려준다. 배우지 않은 액체를 넣었을 때 아무 이름이나
 * 붙이지 않기 위한 안전장치다.
 */
classify_result_t classify_match(const fingerprint_t *fp,
                                 const uint16_t centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS],
                                 uint32_t threshold_d2) {
  classify_result_t r;
  uint32_t best = 0xFFFFFFFFUL;
  int8_t   best_c = -1;
  uint8_t  c, k;

  r.cls  = -1;
  r.d2   = 0xFFFFFFFFUL;
  r.dist = 0;

  if (fp->status != CLASSIFY_OK) {
    return r;
  }

  for (c = 0; c < CLASSIFY_CLASSES; c++) {
    uint32_t d2 = 0;
    for (k = 0; k < CLASSIFY_CHANNELS; k++) {
      int32_t diff = (int32_t)fp->n[k] - (int32_t)centroids[c][k];
      d2 += (uint32_t)(diff * diff);
    }
    if (d2 < best) {
      best   = d2;
      best_c = (int8_t)c;
    }
  }

  r.d2   = best;
  /* 판정에는 제곱거리를 쓰지만, 화면에 보여줄 때는 사람이 감을 잡기 쉬운
     실제 거리가 낫다. 그래서 여기서만 제곱근을 씌운다. */
  r.dist = classify_isqrt(best);
  r.cls  = (best <= threshold_d2) ? best_c : -1;
  return r;
}

/*
 * 정수 제곱근. 뉴턴법(바빌로니아법)이다.
 *
 * 원리는 단순한 반복이다. 답을 x 라고 찍어 놓고, x 와 v/x 의 평균을 새 x 로
 * 삼는 것을 반복한다. x 가 정답보다 크면 v/x 는 정답보다 작으므로, 둘의
 * 평균은 항상 정답 쪽으로 다가간다. 몇 번만 돌면 수렴한다.
 *
 * sqrt() 를 쓰지 않는 이유는 그것이 부동소수점 함수이기 때문이다. 그러면
 * 이 파일 첫머리에서 피하려던 소프트웨어 부동소수점 라이브러리가 통째로
 * 링크되어 Flash 를 1.5~3KB 잡아먹는다.
 *
 * y < x 가 아니라 y >= x 가 되는 순간 멈춘다. 더 줄지 않으면 도착한 것이다.
 * 정수 나눗셈이라 결과는 내림이다 (isqrt(1601) = 40).
 */
uint16_t classify_isqrt(uint32_t v) {
  uint32_t x, y;

  if (v == 0) {
    return 0;
  }
  x = v;
  y = (x + 1) / 2;
  while (y < x) {
    x = y;
    y = (x + v / x) / 2;
  }
  return (uint16_t)x;
}
