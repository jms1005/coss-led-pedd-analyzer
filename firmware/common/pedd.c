/*
 * pedd.c — PEDD 방전 시간 측정 코어 (구현)
 *
 * 측정 원리 (계획서 3.2절)
 *   검출 LED는 캐소드를 PD7(AIN1)에, 애노드를 GND에 연결한다.
 *   PD7을 출력 HIGH로 구동하면 캐소드 전위가 애노드보다 높아져 역방향
 *   바이어스가 걸리고 접합 정전용량이 충전된다.
 *   이어서 PD7을 입력(하이 임피던스)으로 바꾸면, 입사광이 만든 광전류에
 *   의해 전하가 빠져나가면서 핀 전압이 떨어진다.
 *   전압이 내부 1.1V 밴드갭 기준 아래로 내려가는 순간을 Analog Comparator가
 *   감지하고, 그 출력이 Timer1 Input Capture를 트리거해 시각이 하드웨어에
 *   기록된다. 빛이 강할수록 방전이 빨라지므로 측정 시간은 광량에 반비례한다.
 *
 * 소프트웨어 폴링이 아니라 하드웨어 캡처를 쓰는 이유는, 인터럽트 지연이
 * 측정값에 섞이지 않게 하기 위해서다. (계획서 3.4절, 참고문헌 [4] 대응)
 */

#ifndef F_CPU
#define F_CPU 16000000UL
#endif

#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#include <util/delay.h>

#include "pedd.h"

/* ---- 핀 배정 (계획서 3.5절 GPIO 핀 사용량 분석) ---- */
#define DET_DDR   DDRD
#define DET_PORT  PORTD
#define DET_BIT   PD7   /* AIN1. Analog Comparator 음극 입력이라 변경 불가 */

#define EMIT_DDR  DDRB
#define EMIT_PORT PORTB
/*
 * 주의: PB0는 Timer1의 입력 캡처 핀(ICP1)이기도 하다.
 * 다만 아래 pedd_init()에서 ACIC=1로 두면 캡처 소스가 Analog Comparator로
 * 바뀌면서 ICP1 핀이 캡처 회로에서 분리되므로, PB0를 일반 출력(발광 LED
 * 구동)으로 써도 충돌하지 않는다. 계획서 3.5절 핀 배정과 일치한다.
 */
#define EMIT_R    PB0
#define EMIT_G    PB1
#define EMIT_B    PB2

/* ---- 측정 파라미터 ---- */

/*
 * 충전 시간. LED 접합 정전용량은 수십 pF 수준이고 MCU 핀은 수 mA를
 * 공급하므로 이론상 1us 이하면 충분하지만, 브레드보드의 배선 부유 용량을
 * 감안해 여유를 둔다. Phase 1에서 이 값을 바꿔가며 측정값이 변하지 않는
 * 지점(포화 지점)을 확인할 것.
 */
#define CHARGE_US 100

/*
 * Timeout 임계값 (계획서 3.6.2절).
 * Timer1 프리스케일러 /8, 16MHz에서 오버플로우 1회 = 65536 x 500ns = 32.768ms.
 * 61회 = 약 2.0초. 계획서의 예비 목표(1~2초) 상한을 채택했다.
 * Phase 1에서 실측한 암전류 방전 시간 분포를 보고 최종 확정한다.
 */
#define TIMEOUT_OVF 61

/* 파장 전환 시 이전 파장의 잔광 영향을 배제하기 위한 대기 (계획서 6.3절) */
#define SETTLE_MS 5

/* ---- ISR과 공유하는 상태 ---- */
static volatile uint16_t g_ovf;      /* 오버플로우 누적 횟수 */
static volatile uint16_t g_capture;  /* 캡처된 ICR1 값 */
static volatile uint16_t g_cap_ovf;  /* 캡처 시점의 오버플로우 횟수 (보정 반영) */
static volatile uint8_t  g_done;     /* 캡처 완료 플래그 */

/*
 * Timer1 Input Capture 인터럽트.
 * 계획서 3.7절대로 ISR에서는 시각 기록만 하고 연산은 하지 않는다.
 */
ISR(TIMER1_CAPT_vect) {
  uint16_t icr = ICR1;
  uint16_t ovf = g_ovf;

  /*
   * [구현 메모 - 계획서 3.7절] 오버플로우 경계 보정.
   * 캡처 인터럽트(벡터 10)가 오버플로우 인터럽트(벡터 13)보다 우선순위가
   * 높으므로, 오버플로우가 먼저 일어났는데 그 ISR이 아직 실행되지 않은
   * 상태에서 여기로 진입할 수 있다. 그 경우 TOV1 플래그가 아직 세워져 있고
   * ICR1 값은 매우 작다. 이때 오버플로우를 1 더해주지 않으면 32.768ms
   * 단위의 이상값이 간헐적으로 섞여 변동계수 통계가 왜곡된다.
   */
  if ((TIFR1 & (1 << TOV1)) && (icr < 0x8000)) {
    ovf++;
  }

  g_capture = icr;
  g_cap_ovf = ovf;
  g_done = 1;
}

/* Timer1 오버플로우 인터럽트 — 16비트 카운터의 측정 범위를 확장한다. */
ISR(TIMER1_OVF_vect) {
  g_ovf++;
}

/* 발광 LED 전체 소등 */
static void emitters_off(void) {
  EMIT_PORT &= ~((1 << EMIT_R) | (1 << EMIT_G) | (1 << EMIT_B));
}

/* 지정한 발광 LED 하나만 점등 (계획서 3.1절: 한 번에 하나만) */
static void emitter_on(pedd_channel_t ch) {
  emitters_off();
  switch (ch) {
    case PEDD_CH_R: EMIT_PORT |= (1 << EMIT_R); break;
    case PEDD_CH_G: EMIT_PORT |= (1 << EMIT_G); break;
    case PEDD_CH_B: EMIT_PORT |= (1 << EMIT_B); break;
    case PEDD_CH_DARK: default: break;  /* 전체 소등 유지 */
  }
}

void pedd_init(void) {
  /* 발광부: 출력으로 설정하고 소등 상태에서 시작 */
  EMIT_DDR |= (1 << EMIT_R) | (1 << EMIT_G) | (1 << EMIT_B);
  emitters_off();

  /* 검출부: 입력(하이 임피던스), 내부 풀업 해제 */
  DET_DDR  &= ~(1 << DET_BIT);
  DET_PORT &= ~(1 << DET_BIT);

  /*
   * DIDR1의 AIN1D=1 — PD7의 디지털 입력 버퍼를 차단한다.
   * 버퍼가 켜져 있으면 누설 전류가 광전류와 경쟁해 저광량 측정을 왜곡한다.
   * (계획서 6.2절, 8.2절)
   */
  DIDR1 |= (1 << AIN1D);

  /*
   * ADCSRB의 ACME=0 — AIN1(PD7)을 비교기 음극 입력으로 유지한다.
   * 리셋 기본값이 0이지만, 의도를 코드에 남기기 위해 명시적으로 지운다.
   */
  ADCSRB &= ~(1 << ACME);

  /*
   * ACSR 설정
   *   ACD  = 0 : 비교기 활성 상태 유지
   *   ACBG = 1 : 내부 1.1V 밴드갭을 양극 입력으로 선택
   *              (전원 전압과 온도에 따라 흔들리는 논리 문턱값 대신 사용)
   *   ACIC = 1 : 비교기 출력을 Timer1 Input Capture에 연결
   *              이 비트가 0이면 캡처가 아예 발생하지 않는다.
   *   ACIE = 0 : 비교기 자체 인터럽트는 쓰지 않는다 (캡처 인터럽트만 사용)
   */
  ACSR = (1 << ACBG) | (1 << ACIC);

  /*
   * 밴드갭 기준 전압은 활성화 후 안정화 시간이 필요하므로, 매 측정마다
   * 켜고 끄지 않고 초기화 시 한 번 켜서 유지한다. (계획서 6.2절)
   */
  _delay_ms(10);

  /* Timer1: 노멀 모드. 시작은 pedd_measure()에서 한다. */
  TCCR1A = 0;
  TCCR1B = 0;

  /* 입력 캡처 + 오버플로우 인터럽트 활성화 */
  TIMSK1 = (1 << ICIE1) | (1 << TOIE1);
}

pedd_result_t pedd_measure(pedd_channel_t ch) {
  pedd_result_t r;
  uint16_t ovf_now;

  /* ① 파장 선택 — 해당 LED 1개만 점등 */
  emitter_on(ch);
  _delay_ms(SETTLE_MS);

  /* ② 충전 — PD7을 출력 HIGH로 구동해 역방향 바이어스를 건다 */
  DET_PORT |= (1 << DET_BIT);
  DET_DDR  |= (1 << DET_BIT);
  _delay_us(CHARGE_US);

  /* ③ 방전 개시 — 타이머 시작과 핀 해제 사이에 인터럽트가 끼지 않게 막는다 */
  cli();

  g_ovf = 0;
  g_done = 0;
  TCNT1 = 0;

  /*
   * [구현 메모 - 계획서 3.7절] 측정 시작 전 플래그 클리어.
   * AVR에서는 해당 비트에 1을 "기록"해야 클리어된다. 이전 측정의 캡처
   * 플래그가 남아 있으면 타이머 시작 즉시 트리거되어 방전 시간이 0으로
   * 기록된다.
   */
  TIFR1 = (1 << ICF1) | (1 << TOV1);

  /*
   * TCCR1B 설정으로 타이머를 기동한다.
   *   ICES1 = 1 : 상승 에지 캡처.
   *               충전 직후에는 V(PD7) > 1.1V 이므로 ACO = 0 이고,
   *               방전으로 1.1V 아래로 내려가면 ACO가 0->1로 전이한다.
   *               따라서 상승 에지가 맞다. (계획서 6.2절 — 실제 구현 시
   *               오실로스코프로 방전 파형과 캡처 시점을 함께 확인할 것)
   *   CS11  = 1 : 프리스케일러 /8 → 2MHz → 500ns 분해능
   */
  TCCR1B = (1 << ICES1) | (1 << CS11);

  /* 핀을 하이 임피던스로 전환 → 이 순간부터 광전류로 방전이 진행된다.
     타이머를 먼저 켰으므로 몇 클럭(약 125ns)의 고정 오프셋이 생기지만,
     모든 측정에 동일하게 적용되는 상수라 상대 비교에는 영향이 없다. */
  DET_DDR  &= ~(1 << DET_BIT);
  DET_PORT &= ~(1 << DET_BIT);

  sei();

  /* ④ 캡처 완료 또는 Timeout 대기 */
  for (;;) {
    if (g_done) {
      break;
    }
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      ovf_now = g_ovf;
    }
    if (ovf_now >= TIMEOUT_OVF) {
      break;
    }
  }

  /* ⑤ 종료 — 타이머 정지, 발광 LED 소등 */
  TCCR1B = 0;
  emitters_off();

  /* ⑥ 결과 산출. 총 계수 = 캡처값 + (오버플로우 횟수 x 65536) */
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    if (g_done) {
      r.status    = PEDD_OK;
      r.overflows = g_cap_ovf;
      r.ticks     = ((uint32_t)g_cap_ovf << 16) | g_capture;
    } else {
      r.status    = PEDD_TIMEOUT;
      r.overflows = g_ovf;
      r.ticks     = 0;
    }
  }

  return r;
}
