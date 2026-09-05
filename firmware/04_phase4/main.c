/*
 * 04_phase4 — 최종 시스템 (온칩 분류 및 통합)
 *
 * 계획서 1.4절 데모 시나리오 / 4.4절 Phase 4 구현.
 * 설계: docs/superpowers/specs/2026-09-03-phase4-design.md
 *
 * 배선 (계획서 회로도 기준)
 *   D8/D9/D10 (PB0~2)  발광 LED R/G/B
 *   D7  (PD7, AIN1)    검출 LED 캐소드
 *   D2  (PD2)          택트 스위치 - GND 사이. 외부 저항 없음
 *   A4/A5 (PC4/PC5)    OLED SDA/SCL
 *   D13 (PB5)          사이클 시간 측정용 토글 (보드 LED 겸용)
 *   D1  (PD1)          UART TX 38400 8N1
 *
 * 화면 문구는 전부 PSTR() 로 감싸 Flash 에 둔다. AVR 은 일반 문자열
 * 리터럴을 부팅 시 SRAM 으로 복사하는데, 문구가 많아 2KB 를 금방 잠식한다.
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * 이 파일은 부품들을 조립해 하나의 기계로 만드는 자리다. 실제 계산은
 * 전부 common/ 의 모듈이 한다.
 *
 *   pedd.c      빛을 시간으로 재는 일
 *   classify.c  시간을 지문으로 바꾸고 이름을 고르는 일
 *   store.c     배운 것을 전원 꺼도 남기는 일
 *   ssd1306.c   화면에 글자 찍는 일
 *   button.c    버튼 눌림을 짧게/길게로 구분하는 일
 *
 * main() 은 이들을 초기화한 뒤 무한 루프를 돈다. 루프는 20ms 마다 버튼을
 * 한 번 확인하고, 지금 어떤 화면(상태)에 있느냐에 따라 다르게 반응한다.
 * 이런 구조를 상태 기계(state machine)라고 한다. 상태는 5개다.
 *
 *              짧게(학습됨)                     짧게
 *   ST_IDLE ---------------> 측정 -> ST_RESULT ------> ST_IDLE
 *      |                          \                      ^
 *      | 길게                      -> ST_ERROR ----------+
 *      v                                                 |
 *   ST_LEARN_PROMPT --- 3종 다 재면 --> ST_SAVED --------+
 *      |  (짧게: 한 종 측정, 길게: 취소)
 *      +--------------------- 취소 ----------------------+
 *
 * 상태를 이렇게 나눈 이유는, 버튼이 하나뿐이라 "지금 무엇을 하는 중인가"에
 * 따라 같은 누름이 다른 뜻이 되어야 하기 때문이다. ST_IDLE 의 짧게는
 * 측정 시작이지만, ST_RESULT 의 짧게는 대기 화면으로 돌아가기다.
 *
 * 화면과 UART 로 결과를 동시에 내보낸다. OLED 가 없거나 배선이 틀려도
 * UART 로깅은 계속된다 (ssd1306.c 가 실패를 조용히 넘기도록 되어 있다).
 */

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>

#include "pedd.h"
#include "uart.h"
#include "classify.h"
#include "store.h"
#include "ssd1306.h"
#include "button.h"

/*
 * 한 채널을 몇 번 재서 평균낼지.
 * 측정은 3회 — 사용자를 오래 기다리게 하지 않는 선.
 * 학습은 8회 — 이때 만든 중심점이 이후 모든 판정의 기준이 되므로, 시간을
 * 더 쓰더라도 흔들림을 줄이는 편이 낫다.
 */
#define MEASURE_REPEAT        3
#define LEARN_REPEAT          8

/*
 * 이보다 멀면 셋 중 무엇도 아니라고 본다(UNKNOWN).
 * 제곱거리 기준이라 실제 거리로는 sqrt(1600) = 40 이다. 지문 합이 1000 인
 * 척도에서 40 이면 대략 4% 어긋남까지 같은 액체로 인정한다는 뜻이다.
 * 실측 데이터를 모은 뒤 조정할 값이다.
 */
#define DEFAULT_THRESHOLD_D2  1600UL

#define TIMING_DDR   DDRB
#define TIMING_PORT  PORTB
#define TIMING_BIT   PB5

typedef enum {
  ST_IDLE = 0,
  ST_RESULT,
  ST_LEARN_PROMPT,
  ST_SAVED,
  ST_ERROR
} state_t;

/* 클래스 이름도 Flash 에 둔다. */
static const char CLASS_NAME_0[] PROGMEM = "DISTILLED WATER";
static const char CLASS_NAME_1[] PROGMEM = "DYE WATER";
static const char CLASS_NAME_2[] PROGMEM = "MILK";
static const char *const CLASS_NAMES[CLASSIFY_CLASSES] PROGMEM = {
  CLASS_NAME_0, CLASS_NAME_1, CLASS_NAME_2
};

/* "DISTILLED WATER" 15자 + 종단 문자 */
static char g_name_buf[17];

/* Flash 의 클래스 이름을 SRAM 버퍼로 복사해 반환한다. */
static const char *class_name(uint8_t idx) {
  const char *src = (const char *)pgm_read_word(&CLASS_NAMES[idx]);
  uint8_t i;

  for (i = 0; i < sizeof(g_name_buf) - 1; i++) {
    char c = (char)pgm_read_byte(src + i);
    g_name_buf[i] = c;
    if (c == '\0') {
      break;
    }
  }
  g_name_buf[sizeof(g_name_buf) - 1] = '\0';
  return g_name_buf;
}

/* uart.c 를 고치지 않고 Flash 문자열을 보내기 위한 보조 함수 */
static void uart_puts_p(const char *s) {
  char c;

  while ((c = (char)pgm_read_byte(s)) != '\0') {
    uart_putc(c);
    s++;
  }
}

static uint16_t g_centroids[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];
static uint32_t g_threshold = DEFAULT_THRESHOLD_D2;
static uint8_t  g_trained = 0;

/* 마지막 측정 결과 */
static uint32_t g_ticks[4];   /* DARK, R, G, B */
static uint8_t  g_timeout_ch; /* 0=없음, 1=R, 2=G, 3=B */
static fingerprint_t     g_fp;
static classify_result_t g_res;

/* 진행 표시 위치 (문자 단위). DARK R G B 순 */
static const uint8_t SCAN_COL[4] = { 1, 7, 12, 17 };

/* 채널 하나를 repeat회 측정해 평균 틱을 낸다. 전부 타임아웃이면 0을 반환한다. */
static uint32_t measure_avg(pedd_channel_t ch, uint8_t repeat) {
  uint32_t sum = 0;
  uint8_t  ok  = 0;
  uint8_t  i;

  for (i = 0; i < repeat; i++) {
    pedd_result_t r = pedd_measure(ch);
    if (r.status == PEDD_OK) {
      sum += r.ticks;
      ok++;
    }
  }
  if (ok == 0) {
    return 0;
  }
  return sum / ok;
}

/* 스캔 시작 화면. 제목만 바꿔 측정과 학습 양쪽에 쓴다. */
static void screen_scan(const char *title_p, const char *sub) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, title_p);
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  if (sub != 0) {
    ssd1306_puts(2, 0, sub);
  }
  ssd1306_puts_p(4, 0, PSTR("DARK   R    G    B"));
  ssd1306_puts_p(5, 1,  PSTR("-"));
  ssd1306_puts_p(5, 7,  PSTR("-"));
  ssd1306_puts_p(5, 12, PSTR("-"));
  ssd1306_puts_p(5, 17, PSTR("-"));
}

/*
 * DARK, R, G, B 를 순서대로 측정한다.
 * R/G/B 중 타임아웃이 있으면 그 채널 번호를 g_timeout_ch 에 남긴다.
 * DARK 타임아웃은 정상이며 암전류 보정량이 0이 될 뿐이다.
 *
 * 채널 사이에 화면을 갱신하되, PB5 펄스는 채널마다 따로 올렸다 내린다.
 * I2C 통신 시간이 펄스 폭에 섞이면 사이클 처리 시간이 부풀려지기 때문이다.
 * 오실로스코프로는 펄스 4개의 폭을 합산해 읽는다 (계획서 4.4.3절).
 */
static void run_scan(uint8_t repeat) {
  static const pedd_channel_t CH[4] = {
    PEDD_CH_DARK, PEDD_CH_R, PEDD_CH_G, PEDD_CH_B
  };
  uint8_t k;

  for (k = 0; k < 4; k++) {
    TIMING_PORT |= (uint8_t)(1 << TIMING_BIT);
    g_ticks[k] = measure_avg(CH[k], repeat);
    TIMING_PORT &= (uint8_t)~(1 << TIMING_BIT);
    /* 화면 갱신은 펄스 밖에서 한다. */
    ssd1306_puts_p(5, SCAN_COL[k],
                   (g_ticks[k] == 0) ? PSTR("XX") : PSTR("OK"));
  }

  g_timeout_ch = 0;
  if (g_ticks[1] == 0) {
    g_timeout_ch = 1;
  } else if (g_ticks[2] == 0) {
    g_timeout_ch = 2;
  } else if (g_ticks[3] == 0) {
    g_timeout_ch = 3;
  }

  g_fp = classify_fingerprint(g_ticks[0], g_ticks[1], g_ticks[2], g_ticks[3]);
}

/*
 * 화면 폭에 맞춘 우측 정렬 숫자. buf 는 width+1 바이트 이상이어야 한다.
 *
 * sprintf() 를 쓰지 않고 직접 만든 이유는 크기 때문이다. sprintf 를 한 번
 * 부르는 순간 표준 입출력 라이브러리가 통째로 링크되어 Flash 를 수 KB
 * 잡아먹는다. 대회 채점에 메모리 사용량이 들어가므로 이 정도 함수는
 * 손으로 쓰는 편이 낫다. (uart.c 의 uart_put_u32 도 같은 이유다)
 *
 * 나머지 연산으로 낮은 자리부터 뽑히므로 버퍼 뒤에서 앞으로 채운다.
 */
static void fmt_u32(char *buf, uint8_t width, uint32_t v) {
  uint8_t i = width;

  buf[width] = '\0';
  while (i > 0) {
    i--;
    buf[i] = (char)('0' + (uint8_t)(v % 10));
    v /= 10;
    if (v == 0) {
      break;
    }
  }
  while (i > 0) {
    i--;
    buf[i] = ' ';
  }
}

/*
 * CSV 헤더. 부팅 시 한 번만 내보낸다.
 * 측정마다 반복하면 터미널로 받은 로그 파일에 헤더가 섞여 분석이 깨진다.
 */
static void log_uart_header(void) {
  uart_puts_p(PSTR("# LED PEDD ANALYZER PHASE4"));
  uart_newline();
  uart_puts_p(PSTR("DARK,R,G,B,n0,n1,n2,cls,d2"));
  uart_newline();
}

static void log_uart(void) {
  uart_put_u32(g_ticks[0]); uart_putc(',');
  uart_put_u32(g_ticks[1]); uart_putc(',');
  uart_put_u32(g_ticks[2]); uart_putc(',');
  uart_put_u32(g_ticks[3]); uart_putc(',');
  uart_put_u32(g_fp.n[0]);  uart_putc(',');
  uart_put_u32(g_fp.n[1]);  uart_putc(',');
  uart_put_u32(g_fp.n[2]);  uart_putc(',');
  if (g_res.cls < 0) {
    uart_puts_p(PSTR("UNKNOWN"));
  } else {
    uart_puts(class_name((uint8_t)g_res.cls));
  }
  uart_putc(',');
  uart_put_u32(g_res.d2);
  uart_newline();
}

static void screen_result(void) {
  char buf[8];

  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("RESULT:"));
  if (g_res.cls < 0) {
    ssd1306_puts_p(0, 9, PSTR("UNKNOWN"));
  } else {
    ssd1306_puts(0, 9, class_name((uint8_t)g_res.cls));
  }
  ssd1306_puts_p(1, 0, PSTR("---------------------"));

  ssd1306_puts_p(2, 0, PSTR("R"));
  fmt_u32(buf, 7, pedd_ticks_to_us(g_ticks[1]));
  ssd1306_puts(2, 3, buf);
  ssd1306_puts_p(2, 11, PSTR("US"));

  ssd1306_puts_p(3, 0, PSTR("G"));
  fmt_u32(buf, 7, pedd_ticks_to_us(g_ticks[2]));
  ssd1306_puts(3, 3, buf);
  ssd1306_puts_p(3, 11, PSTR("US"));

  ssd1306_puts_p(4, 0, PSTR("B"));
  fmt_u32(buf, 7, pedd_ticks_to_us(g_ticks[3]));
  ssd1306_puts(4, 3, buf);
  ssd1306_puts_p(4, 11, PSTR("US"));

  ssd1306_puts_p(5, 0, PSTR("DARK"));
  fmt_u32(buf, 7, pedd_ticks_to_us(g_ticks[0]));
  ssd1306_puts(5, 5, buf);
  ssd1306_puts_p(5, 13, PSTR("US"));

  ssd1306_puts_p(6, 0, PSTR("DIST"));
  fmt_u32(buf, 5, g_res.dist);
  ssd1306_puts(6, 5, buf);
  ssd1306_puts_p(6, 11, PSTR("THR"));
  fmt_u32(buf, 5, classify_isqrt(g_threshold));
  ssd1306_puts(6, 15, buf);
}

static void screen_idle(void) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("LED PEDD ANALYZER"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  if (g_trained) {
    ssd1306_puts_p(3, 0, PSTR("READY"));
    ssd1306_puts_p(5, 0, PSTR("SHORT: MEASURE"));
    ssd1306_puts_p(6, 0, PSTR("LONG : LEARN"));
  } else {
    ssd1306_puts_p(3, 0, PSTR("NOT TRAINED"));
    ssd1306_puts_p(5, 0, PSTR("HOLD BTN 2S TO LEARN"));
  }
}

static void screen_learn_prompt(uint8_t idx) {
  ssd1306_clear();
  if (idx == 0) {
    ssd1306_puts_p(0, 0, PSTR("LEARN 1/3"));
  } else if (idx == 1) {
    ssd1306_puts_p(0, 0, PSTR("LEARN 2/3"));
  } else {
    ssd1306_puts_p(0, 0, PSTR("LEARN 3/3"));
  }
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  ssd1306_puts(3, 0, class_name(idx));
  ssd1306_puts_p(5, 0, PSTR("SHORT: MEASURE"));
  ssd1306_puts_p(6, 0, PSTR("LONG : CANCEL"));
}

static void screen_error(void) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("ERROR"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  if (g_timeout_ch == 1) {
    ssd1306_puts_p(3, 0, PSTR("TIMEOUT: R"));
  } else if (g_timeout_ch == 2) {
    ssd1306_puts_p(3, 0, PSTR("TIMEOUT: G"));
  } else if (g_timeout_ch == 3) {
    ssd1306_puts_p(3, 0, PSTR("TIMEOUT: B"));
  } else {
    ssd1306_puts_p(3, 0, PSTR("LOW SIGNAL"));
  }
  ssd1306_puts_p(5, 0, PSTR("CHECK LED POLARITY"));
  ssd1306_puts_p(6, 0, PSTR("SHORT: BACK"));
}

static void screen_saved(void) {
  ssd1306_clear();
  ssd1306_puts_p(0, 0, PSTR("SAVED TO EEPROM"));
  ssd1306_puts_p(1, 0, PSTR("---------------------"));
  ssd1306_puts_p(3, 0, PSTR("3 CLASSES STORED"));
  ssd1306_puts_p(6, 0, PSTR("SHORT: BACK"));
}

int main(void) {
  state_t  state = ST_IDLE;
  uint8_t  learn_idx = 0;   /* 지금 몇 번째 액체를 배우는 중인가 (0~2) */
  /* 학습 중 모은 지문. 3종을 다 채운 뒤에야 g_centroids 로 옮긴다.
     중간에 취소하면 이 배열만 버려지고 기존 학습은 그대로 남는다. */
  uint16_t learn_acc[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];

  TIMING_DDR |= (uint8_t)(1 << TIMING_BIT);
  uart_init();
  pedd_init();
  button_init();
  ssd1306_init();   /* 실패해도 계속 진행한다. UART 로깅은 살아 있어야 한다. */
  sei();            /* 전역 인터럽트 허용. pedd.c 의 캡처 ISR 이 이때부터 동작한다. */

  log_uart_header();

  /* 지난번에 배운 것이 EEPROM 에 남아 있으면 그대로 이어서 쓴다.
     없거나 깨졌으면 g_trained 가 0 이 되어 화면에 NOT TRAINED 가 뜬다. */
  g_trained = store_load(g_centroids, &g_threshold);
  if (!g_trained) {
    g_threshold = DEFAULT_THRESHOLD_D2;
  }
  screen_idle();

  /*
   * 메인 루프. 20ms 마다 버튼을 한 번 보고, 현재 상태에 맞게 반응한다.
   * 측정이나 화면 갱신은 이 루프 안에서 그때그때 끝내므로 별도의 작업
   * 큐나 타이머가 없다. 파일 첫머리의 상태 전이 그림과 함께 읽으면 된다.
   */
  for (;;) {
    button_event_t ev = button_poll();
    _delay_ms(BUTTON_POLL_MS);

    switch (state) {
      case ST_IDLE:
        if (ev == BTN_SHORT && g_trained) {
          screen_scan(PSTR("MEASURING..."), 0);
          run_scan(MEASURE_REPEAT);
          g_res = classify_match(&g_fp,
                    (const uint16_t (*)[CLASSIFY_CHANNELS])g_centroids,
                    g_threshold);
          log_uart();
          if (g_timeout_ch != 0 || g_fp.status != CLASSIFY_OK) {
            screen_error();
            state = ST_ERROR;
          } else {
            screen_result();
            state = ST_RESULT;
          }
        } else if (ev == BTN_LONG) {
          learn_idx = 0;
          screen_learn_prompt(learn_idx);
          state = ST_LEARN_PROMPT;
        }
        break;

      case ST_RESULT:
      case ST_ERROR:
      case ST_SAVED:
        if (ev == BTN_SHORT) {
          screen_idle();
          state = ST_IDLE;
        }
        break;

      case ST_LEARN_PROMPT:
        if (ev == BTN_LONG) {
          /* 취소. EEPROM 은 건드리지 않아 기존 학습이 보존된다. */
          screen_idle();
          state = ST_IDLE;
        } else if (ev == BTN_SHORT) {
          uint8_t k;

          screen_scan(PSTR("LEARNING"), class_name(learn_idx));
          run_scan(LEARN_REPEAT);
          g_res.cls  = -1;
          g_res.d2   = 0;
          g_res.dist = 0;
          log_uart();

          if (g_timeout_ch != 0 || g_fp.status != CLASSIFY_OK) {
            screen_error();
            state = ST_ERROR;
            break;
          }
          for (k = 0; k < CLASSIFY_CHANNELS; k++) {
            learn_acc[learn_idx][k] = g_fp.n[k];
          }
          learn_idx++;

          /* 3종을 다 모았을 때만 실제 중심점에 반영하고 EEPROM 에 쓴다.
             중간에 그만두면 아무것도 바뀌지 않는다. */
          if (learn_idx >= CLASSIFY_CLASSES) {
            uint8_t c;
            for (c = 0; c < CLASSIFY_CLASSES; c++) {
              for (k = 0; k < CLASSIFY_CHANNELS; k++) {
                g_centroids[c][k] = learn_acc[c][k];
              }
            }
            g_threshold = DEFAULT_THRESHOLD_D2;
            store_save((const uint16_t (*)[CLASSIFY_CHANNELS])g_centroids,
                       g_threshold);
            g_trained = 1;
            screen_saved();
            state = ST_SAVED;
          } else {
            screen_learn_prompt(learn_idx);
          }
        }
        break;

      default:
        state = ST_IDLE;
        break;
    }
  }
}
