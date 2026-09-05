# 전기·빛 흐름 그림

[`docs/쉬운_설명.md`](../../docs/쉬운_설명.md) 에 들어가는 그림 3장입니다.
처음 보는 사람에게 **전기가 어디서 시작해 어떻게 흐르는지**를 보여주는 것이
목적입니다.

| 파일 | 내용 |
|---|---|
| `flow1.svg` | 발광 LED 회로 — USB에서 출발해 GND로 돌아오는 한 바퀴 |
| `flow2.svg` | 검출 LED — 충전과 방전 2단계, 그리고 전압이 1.1V로 떨어지는 곡선 |
| `flow3.svg` | 빛과 정보의 흐름 — 발광 → 액체 → 검출 → 판정 → 화면 |
| `png/flow1~3.png` | 위 3장의 2배 배율 PNG |

## SVG 와 PNG 를 둘 다 두는 이유

| 형식 | 쓰는 곳 |
|---|---|
| PNG | `docs/쉬운_설명.md`, GitHub 웹 |
| SVG | 인쇄, 발표 슬라이드, Word/PowerPoint 삽입 |

GitHub 는 마크다운 안의 SVG 를 보안 필터를 거쳐 보여주는데, 이때 글꼴이
보는 사람 컴퓨터의 기본 글꼴로 바뀌어 글자 간격이 달라질 수 있습니다.
그래서 **문서는 PNG 를 참조**하고, SVG 는 배율이 중요한 인쇄·슬라이드용으로
남겨 둡니다.

## 배선도(`figures/wiring`)와 다른 점

| | 배선도 | 이 그림 |
|---|---|---|
| 답하는 질문 | **어느 구멍에** 꽂는가 | **왜 그렇게** 꽂는가 |
| 보는 사람 | 직접 조립하는 사람 | 프로젝트를 처음 보는 사람 |
| 형식 | A4 인쇄용 (세로) | 화면용 (가로) |

그래서 이 그림들은 `build_drawings_lib` 의 A4 `Sheet` 틀을 쓰지 않고
색과 글꼴만 공유합니다.

## 만들기

```sh
sh tools/make_flow_png.sh              # SVG 3장 + PNG 3장 (권장)
python tools/make_flow_drawings.py     # SVG 만 다시
```

PNG 렌더링에는 Chrome 이 필요합니다 (`render_figures.sh` 와 같은 방식).
**생성물을 직접 고치지 마세요.** 다음 실행 때 사라집니다.

## 핀 번호를 바꾸려면

`tools/make_flow_drawings.py` 를 고치는 것으로는 부족합니다.
**펌웨어가 먼저**입니다 (`firmware/common/pedd.c` 의 발광 PB0/PB1/PB2,
검출 PD7). 그다음 이 그림과 `figures/wiring` 을 함께 다시 만드세요.
