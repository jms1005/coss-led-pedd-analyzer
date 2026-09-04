# 배선도 사용법

부품이 도착한 뒤 브레드보드에 배선할 때 보는 A4 4장입니다.
**핀 배정의 출처는 펌웨어**이며, 도면은 그것을 그림으로 옮긴 것입니다.

| 장 | 내용 |
|---|---|
| 1 | 한눈에 보기 — 연결 요약, 핀 대응표, LED 다리 구별법 |
| 2 | 브레드보드 배치도 — 몇 번 구멍에 꽂는지 |
| 3 | 연결 순서 6단계 |
| 4 | 연결 확인표 26칸 + 문제 생겼을 때 볼 곳 |

## 만들기

```
sh tools/make_wiring_pdf.sh            # SVG 4장 + docs/배선도.pdf 까지
python tools/make_wiring_drawings.py   # SVG 만 다시
```

## 제작 도면과 다른 점 — 실척이 아닙니다

`docs/제작도면.pdf`(차광 챔버)의 2·3·4장은 오려서 우드락에 대고 자르는
**1:1 실척 템플릿**이라 인쇄 배율이 중요합니다.

**배선도는 실척이 아닙니다.** 구멍 번호를 보고 꽂는 지도이므로 배율은
상관없습니다. 다만 글자가 작으니 축소 인쇄는 피하세요.
4장(확인표)은 손으로 체크하며 쓰는 장이라 꼭 인쇄하시길 권합니다.

## 핀 배정을 바꾸려면

`tools/make_wiring_drawings.py` 의 `PINS` 를 고치는 것으로는 부족합니다.
**펌웨어가 먼저**입니다.

| 핀 | 쓰임 | 정의된 곳 |
|---|---|---|
| PB0 / PB1 / PB2 | 발광 LED 적·녹·청 | `firmware/common/pedd.c` |
| PD7 | 검출 LED 캐소드 (AIN1) | `firmware/common/pedd.c` |
| PD2 | 버튼 (내부 풀업) | `firmware/common/button.c` |
| PC4 / PC5 | OLED SDA / SCL | `firmware/common/i2c.c` |
| PB5 | 타이밍 관측용 (보드 내장 LED) | `firmware/04_phase4/main.c` |

**PD7 은 바꿀 수 없습니다.** Analog Comparator 의 음극 입력(AIN1)이
이 핀에 고정되어 있어서, 다른 핀으로 옮기면 측정 원리 자체가 성립하지
않습니다.

PB5 는 오실로스코프로 방전 파형을 볼 때만 쓰므로 배선하지 않아도 됩니다.

## 브레드보드 자리 배정

`make_wiring_drawings.py` 위쪽의 `CH`, `DET_K/DET_A`, `SW_C1/SW_C2` 가
열 번호를 정합니다. 옮길 때는 **위쪽 반(A~E)과 아래쪽 반(F~J)이 같은
열이라도 서로 이어져 있지 않다**는 점만 지키면 됩니다.

현재 배정에서 위쪽 반은 2·6·8·11·15·17·20·24·26·28 열을,
아래쪽 반은 3·5·30 열을 씁니다. 겹치지 않게 잡아 둔 값입니다.

## 구성

| 파일 | 역할 |
|---|---|
| `tools/build_drawings_lib.py` | 도형·치수선 그리기 도구 (제작 도면과 공용) |
| `tools/make_wiring_drawings.py` | 브레드보드 그리기 + 시트 4장 내용 |
| `figures/wiring/wire1~4.svg` | 생성물. **직접 고치지 마세요** |
| `figures/wiring/print.html` | A4 인쇄 래퍼 |
| `tools/make_wiring_pdf.sh` | 위를 묶어 `docs/배선도.pdf` 생성 |
