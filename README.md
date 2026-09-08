# LED 다파장 재이용 광검출 기반 저비용 액체 광학 분석기

2026 COSS 차세대반도체 MCU 응용 경진대회 출품작.

LED를 **발광 소자이자 광검출 소자로 동시에 사용**하는 PEDD(Paired
Emitter–Detector Diode) 방식으로 액체 시료를 판별한다. 포토다이오드나 전용
광센서 없이 LED 4개만으로 광학 분석기를 구성해 원가를 낮추는 것이 목표다.

> 처음 보는 분은 [**쉬운 설명**](docs/쉬운_설명.md)부터 읽으세요.
> 전자공학을 몰라도 되도록, 전기가 어디서 시작해 어떻게 흐르는지 그림으로
> 설명합니다.

## 동작 원리

검출용 LED를 역방향 바이어스로 충전한 뒤 방전 시간을 측정한다. 빛이 많이
들어올수록 방전이 빨라진다. 이 시간을 Analog Comparator + Timer1 입력
캡처로 재고, R·G·B 세 파장에 대해 반복해 **광학 지문 벡터**를 만든다.

```
버튼 → DARK/R/G/B 스캔 → 암전류 보정 → 정규화 → 최근접 중심점 분류 → OLED + UART
```

## 제약

대회 요강상 **Arduino IDE와 외부 라이브러리를 쓸 수 없다.** 개발 환경은
Microchip Studio이고 모든 주변장치를 레지스터 직접 제어로 다룬다.
MCU 사용 핀 수·부품 가격·코드/데이터 메모리 크기가 모두 채점에 반영된다.

- MCU: ATmega328P (16MHz)
- 사용 핀: 9개
- 부동소수점 미사용 (전 구간 32비트 정수 연산)

## 구성

```
firmware/          펌웨어 (Microchip Studio 솔루션)
  common/            공유 모듈
  01_blink/          툴체인 검증
  02_phase1/         단일 채널 측정
  03_phase2/         RGB 다파장 스캔
  04_phase4/         최종 시스템 (버튼 + OLED + 온칩 분류)
tests/             호스트 단위 테스트
tools/             도면 생성 · 문서 빌드 · 테스트 러너 · 분석 스크립트
figures/           블록도 · 흐름도 · 회로도 · 배선도 · 제작도면
docs/              제작 가이드 · 측정 프로토콜 · 설명 문서
  superpowers/       설계 스펙 및 구현 계획
data/              측정 데이터 (실험 후 채움)
제출물/            대회 제출용 산출물
공모전자료/        주최측 배포 안내문 (참고용)
backup/            계획서 원본 스냅샷 (insert_figures.py 가 사용)
```

## 메모리 사용량

| 프로젝트 | Flash (32KB) | SRAM (2KB) |
|---|---:|---:|
| 01_blink | 176 B (0.5%) | 0 B (0.0%) |
| 02_phase1 | 1,430 B (4.4%) | 89 B (4.3%) |
| 03_phase2 | 1,360 B (4.2%) | 121 B (5.9%) |
| **04_phase4** | **6,690 B (20.4%)** | **90 B (4.4%)** |

## 빌드와 테스트

**펌웨어** — `firmware/PEDD.atsln`을 Microchip Studio로 열고 `F7`.
자세한 내용은 [`firmware/README.md`](firmware/README.md) 참조.

**호스트 단위 테스트** — 분류 로직은 하드웨어 없이 PC에서 검증한다.

```sh
sh tools/run_host_tests.sh
```

`firmware/common/classify.c`는 이 테스트를 위해 `<avr/io.h>`를 포함하지
않는다. **이 조건을 깨뜨리면 테스트가 빌드되지 않는다.**

## 진행 상태

- [x] 계획서 · 회로도 · 부품 목록
- [x] Phase 1~2 펌웨어 (실험용)
- [x] Phase 4 펌웨어 (최종 시스템)
- [ ] 하드웨어 조립 및 측정 — [브링업 체크리스트](docs/superpowers/plans/2026-09-03-phase4-bringup.md)
- [ ] 예선 제출물 (PPT · 동영상)

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/쉬운_설명.md`](docs/쉬운_설명.md) | **비전공자용 소개** — 동작 원리와 전기 흐름을 그림으로 |
| [`docs/판별_로직_설명.md`](docs/판별_로직_설명.md) | `classify.c` 판별 흐름을 말로 설명하기 위한 정리 |
| [`firmware/README.md`](firmware/README.md) | 툴체인 설정, 배선표, 자주 막히는 지점 |
| [`docs/superpowers/specs/2026-09-03-phase4-design.md`](docs/superpowers/specs/2026-09-03-phase4-design.md) | Phase 4 설계 근거, 정수 연산 오버플로우 분석 |
| [`docs/측정_프로토콜.md`](docs/측정_프로토콜.md) | 실측 절차와 판정 기준 |
| [`docs/실수_방지_체크리스트.md`](docs/실수_방지_체크리스트.md) | 배선·브링업에서 자주 나는 실수와 예방 절차 |
| [`docs/차광챔버_제작.md`](docs/차광챔버_제작.md) | 차광 챔버 · 큐벳 선정과 제작 |
| [`구매목록.md`](구매목록.md) | 부품 선정 근거 (검출 LED 색상이 중요) |
