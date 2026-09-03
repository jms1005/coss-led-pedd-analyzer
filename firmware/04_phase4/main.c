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

#define MEASURE_REPEAT        3
#define LEARN_REPEAT          8
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

/* 화면 폭에 맞춘 우측 정렬 숫자. buf 는 width+1 바이트 이상이어야 한다. */
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

static void log_uart(void) {
  uart_puts_p(PSTR("DARK,R,G,B,n0,n1,n2,cls,d2"));
  uart_newline();
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
  uint8_t  learn_idx = 0;
  uint16_t learn_acc[CLASSIFY_CLASSES][CLASSIFY_CHANNELS];

  TIMING_DDR |= (uint8_t)(1 << TIMING_BIT);
  uart_init();
  pedd_init();
  button_init();
  ssd1306_init();   /* 실패해도 계속 진행한다. UART 로깅은 살아 있어야 한다. */
  sei();

  g_trained = store_load(g_centroids, &g_threshold);
  if (!g_trained) {
    g_threshold = DEFAULT_THRESHOLD_D2;
  }
  screen_idle();

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
