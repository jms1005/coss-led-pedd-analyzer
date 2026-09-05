/*
 * ssd1306.c — OLED 드라이버
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * SSD1306 은 128x64 흑백 OLED 모듈에 들어 있는 제어 칩 이름이다.
 * i2c.c 를 통해 이 칩에게 명령과 그림 데이터를 보낸다.
 *
 * 화면 좌표가 특이하다. 세로 64픽셀을 8픽셀씩 묶어 "페이지" 8줄로 나누고,
 * 한 번에 1바이트(=세로 8픽셀 한 칸)씩 보낸다. 바이트의 비트 0이 맨 위
 * 픽셀, 비트 7이 맨 아래 픽셀이다.
 *
 *      가로 128칸 ------------------->
 *   페이지 0 [8픽셀] [8픽셀] [8픽셀] ...
 *   페이지 1 [8픽셀] [8픽셀] ...
 *   ...  (페이지 7 까지)
 *
 * 글꼴이 6x8 인 것은 이 구조에 딱 맞기 때문이다. 세로 8픽셀 = 정확히 한
 * 페이지라서 한 글자가 1바이트짜리 세로줄 6개면 끝난다. 그래서 한 줄에
 * 128/6 = 21글자, 8줄이 들어간다.
 *
 * 이 파일의 함수는 실패해도 아무 말 없이 그냥 돌아온다(g_ready 검사).
 * 화면이 없거나 배선이 틀려도 측정과 UART 로깅은 계속되어야 하기 때문이다.
 * 실험 도중 디스플레이 문제로 데이터 수집이 멈추면 안 된다.
 *
 * 명령 바이트 앞에 0x00, 그림 데이터 앞에 0x40 을 붙이는 것은 SSD1306 이
 * 둘을 구분하는 방식이다 (CTRL_CMD / CTRL_DATA).
 */

#include <avr/pgmspace.h>

#include "ssd1306.h"
#include "i2c.h"
#include "font6x8.h"

#define CTRL_CMD   0x00
#define CTRL_DATA  0x40

/* 초기화에 실패하면 이후 모든 출력을 건너뛴다. */
static uint8_t g_ready = 0;

/* 데이터시트 권장 초기화 시퀀스 (128x64) */
static const uint8_t INIT_SEQ[] PROGMEM = {
  0xAE,        /* 디스플레이 끄기 */
  0xD5, 0x80,  /* 클럭 분주 */
  0xA8, 0x3F,  /* 멀티플렉스 비율 = 64 */
  0xD3, 0x00,  /* 표시 오프셋 없음 */
  0x40,        /* 시작 라인 0 */
  0x8D, 0x14,  /* 차지 펌프 켜기 (모듈이 자체 승압) */
  0x20, 0x02,  /* 페이지 주소 모드 */
  0xA1,        /* 좌우 반전 - 일반적인 모듈 배치 기준 */
  0xC8,        /* 상하 반전 */
  0xDA, 0x12,  /* COM 핀 배치 */
  0x81, 0x7F,  /* 밝기 */
  0xD9, 0xF1,  /* 프리차지 */
  0xDB, 0x40,  /* VCOMH */
  0xA4,        /* RAM 내용 표시 */
  0xA6,        /* 정상 표시 (반전 아님) */
  0xAF         /* 디스플레이 켜기 */
};

static uint8_t cmd(uint8_t c) {
  if (!i2c_start(SSD1306_ADDR, 0)) {
    return 0;
  }
  if (!i2c_write(CTRL_CMD)) {
    i2c_stop();
    return 0;
  }
  if (!i2c_write(c)) {
    i2c_stop();
    return 0;
  }
  i2c_stop();
  return 1;
}

/*
 * 커서를 (page, 픽셀 x) 로 옮긴다.
 * 가로 좌표는 0~127 이라 한 명령에 안 들어간다. SSD1306 은 이를 4비트씩
 * 둘로 쪼개 받도록 되어 있어서, 명령을 두 번 보낸다.
 */
static uint8_t set_pos(uint8_t page, uint8_t x) {
  if (!cmd((uint8_t)(0xB0 | (page & 0x07)))) {       /* 0xB0 + 페이지 번호 */
    return 0;
  }
  if (!cmd((uint8_t)(0x00 | (x & 0x0F)))) {          /* 하위 니블 */
    return 0;
  }
  return cmd((uint8_t)(0x10 | ((x >> 4) & 0x0F)));   /* 상위 니블 */
}

void ssd1306_clear(void) {
  uint8_t page, i;

  if (!g_ready) {
    return;
  }
  for (page = 0; page < SSD1306_PAGES; page++) {
    if (!set_pos(page, 0)) {
      return;
    }
    if (!i2c_start(SSD1306_ADDR, 0)) {
      return;
    }
    if (!i2c_write(CTRL_DATA)) {
      i2c_stop();
      return;
    }
    for (i = 0; i < SSD1306_COLS; i++) {
      if (!i2c_write(0x00)) {
        break;
      }
    }
    i2c_stop();
  }
}

uint8_t ssd1306_init(void) {
  uint8_t i;

  g_ready = 0;
  i2c_init();
  for (i = 0; i < sizeof(INIT_SEQ); i++) {
    if (!cmd(pgm_read_byte(&INIT_SEQ[i]))) {
      return 0;
    }
  }
  g_ready = 1;
  ssd1306_clear();
  return 1;
}

/*
 * 문자열 출력 공통 구현.
 * from_pgm 이 1이면 s 는 Flash(PROGMEM) 주소, 0이면 SRAM 주소다.
 */
static void puts_impl(uint8_t page, uint8_t col, const char *s, uint8_t from_pgm) {
  uint8_t x;

  if (!g_ready || page >= SSD1306_PAGES) {
    return;
  }
  x = (uint8_t)(col * FONT_WIDTH);
  if (!set_pos(page, x)) {
    return;
  }
  if (!i2c_start(SSD1306_ADDR, 0)) {
    return;
  }
  if (!i2c_write(CTRL_DATA)) {
    i2c_stop();
    return;
  }
  while ((uint16_t)(x + FONT_WIDTH) <= SSD1306_COLS) {
    uint8_t c = from_pgm ? (uint8_t)pgm_read_byte(s) : (uint8_t)*s;
    uint8_t i;
    if (c == 0) {
      break;
    }
    s++;
    /* 폰트 범위 밖(소문자 등)은 공백으로 대체한다. */
    if (c < FONT_FIRST_CHAR || c > FONT_LAST_CHAR) {
      c = ' ';
    }
    for (i = 0; i < FONT_WIDTH; i++) {
      if (!i2c_write(pgm_read_byte(&FONT6X8[c - FONT_FIRST_CHAR][i]))) {
        i2c_stop();
        return;
      }
    }
    x = (uint8_t)(x + FONT_WIDTH);
  }
  i2c_stop();
}

void ssd1306_puts(uint8_t page, uint8_t col, const char *s) {
  puts_impl(page, col, s, 0);
}

void ssd1306_puts_p(uint8_t page, uint8_t col, const char *s) {
  puts_impl(page, col, s, 1);
}
