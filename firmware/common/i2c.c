/*
 * i2c.c — TWI 마스터
 *
 * ---- 처음 읽는 사람을 위한 요약 ----
 *
 * I2C 는 선 2가닥(SDA=데이터, SCL=클럭)으로 여러 부품과 대화하는 규약이다.
 * 우리는 OLED 화면 하나에게만 말을 건다. TWI 는 이 I2C 를 가리키는
 * Atmel 쪽 이름이라 레지스터 이름이 전부 TW 로 시작한다 (같은 것이다).
 *
 * 대화는 늘 같은 모양이다.
 *
 *   start(주소) -> write(바이트) -> write(바이트) -> ... -> stop()
 *
 * 말을 거는 쪽이 마스터(우리), 대답하는 쪽이 슬레이브(OLED)다. 마스터가
 * 먼저 "지금부터 말한다"(START)고 알리고, 누구에게 하는 말인지 7비트
 * 주소로 지목한다. 슬레이브는 바이트를 받을 때마다 "받았다"(ACK)고
 * 답한다. 이 ACK 가 안 오면 배선이 끊겼거나 주소가 틀린 것이다.
 *
 * 아래 함수들이 0 을 반환하면 그런 실패다. 호출하는 ssd1306.c 는 실패를
 * 조용히 넘기도록 만들어져 있다. 화면이 없거나 잘못 꽂혀 있어도 UART
 * 로깅과 측정은 계속되어야 하기 때문이다.
 *
 * 하드웨어가 한 단계를 끝내면 TWINT 비트를 1로 세운다. 그래서 코드가
 * "레지스터에 명령 쓰기 -> TWINT 가 설 때까지 대기" 를 반복하는 모양이 된다.
 */

#include <avr/io.h>

#include "i2c.h"

/*
 * SCL = F_CPU / (16 + 2 * TWBR * 4^TWPS)
 * TWPS = 0, TWBR = 12 -> 16000000 / (16 + 24) = 400kHz
 * SSD1306은 400kHz를 지원한다. 화면 갱신 속도에 직접 영향을 준다.
 */
#define I2C_TWBR_400K  12

/*
 * TWINT 대기 상한. 슬레이브가 없을 때 무한 대기를 막는다.
 * OLED 를 안 꽂았거나 배선이 틀리면 TWINT 가 영원히 서지 않는데, 상한이
 * 없으면 여기서 프로그램이 멈춰 측정도 UART 도 죽는다. 반드시 필요하다.
 */
#define I2C_GUARD  20000u

/* TWINT 가 설 때까지 기다린다. 1 = 정상, 0 = 상한 초과(응답 없음). */
static uint8_t wait_twint(void) {
  uint16_t guard = 0;
  while (!(TWCR & (1 << TWINT))) {
    if (++guard >= I2C_GUARD) {
      return 0;
    }
  }
  return 1;
}

void i2c_init(void) {
  TWSR = 0;                 /* 프리스케일러 1 */
  TWBR = I2C_TWBR_400K;
  TWCR = (1 << TWEN);
}

/*
 * START 를 보내고 이어서 상대 주소를 지목한다.
 * addr7 은 7비트 주소, read 는 0=쓰기 / 1=읽기. 반환 1 이면 상대가 응답했다.
 */
uint8_t i2c_start(uint8_t addr7, uint8_t read) {
  uint8_t status;

  /* TWSTA = START 조건을 내보내라. TWINT 에 1을 쓰는 것이 "실행" 신호다
     (AVR 은 이런 플래그를 1을 써서 지우고 다음 동작을 시작시킨다). */
  TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  status = (uint8_t)(TWSR & 0xF8);
  /* 0x08 = START 전송됨, 0x10 = 반복 START 전송됨 */
  if (status != 0x08 && status != 0x10) {
    return 0;
  }

  /*
   * 주소 바이트를 만든다. I2C 는 7비트 주소를 위쪽 7칸에 싣고, 맨 아래
   * 1비트로 읽기/쓰기를 표시하는 규약이다. 그래서 왼쪽으로 한 칸 밀고
   * 마지막 비트에 방향을 넣는다.
   */
  TWDR = (uint8_t)((addr7 << 1) | (read ? 1 : 0));
  TWCR = (1 << TWINT) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  status = (uint8_t)(TWSR & 0xF8);
  /* 0x18 = SLA+W 에 ACK, 0x40 = SLA+R 에 ACK */
  return (uint8_t)((status == 0x18 || status == 0x40) ? 1 : 0);
}

uint8_t i2c_write(uint8_t data) {
  TWDR = data;
  TWCR = (1 << TWINT) | (1 << TWEN);
  if (!wait_twint()) {
    return 0;
  }
  /* 0x28 = 데이터 전송 후 ACK */
  return (uint8_t)(((TWSR & 0xF8) == 0x28) ? 1 : 0);
}

void i2c_stop(void) {
  uint16_t guard = 0;
  TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
  /* STOP 완료는 TWSTO 가 자동으로 내려가는 것으로 확인한다. */
  while (TWCR & (1 << TWSTO)) {
    if (++guard >= I2C_GUARD) {
      return;
    }
  }
}
