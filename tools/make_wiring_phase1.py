# -*- coding: utf-8 -*-
"""
make_wiring_phase1.py — Phase 1 전용 배선도 1장 생성

전체 배선도(make_wiring_drawings.py)는 최종 시스템 26칸 기준이라 Phase 1
에서는 절반 이상이 쓰이지 않는다. 이 도면은 **Phase 1 펌웨어가 실제로
건드리는 11칸만** 담은 1장짜리다.

  firmware/02_phase1/main.c 는 DARK 와 R 두 채널만 측정한다.
  따라서 녹·청 발광 LED(PB1/PB2), 버튼(PD2), OLED(PC4/PC5)는 배선하지
  않는다. 쓰지 않는 LED 를 챔버에 넣으면 산란광이라는 오차 요인만 는다.

부품 그리기 함수와 열 배정은 전체 배선도와 **같은 출처를 쓴다.**
따로 베껴 두면 한쪽만 고쳤을 때 두 도면이 어긋나기 때문이다.

실행:  python tools/make_wiring_phase1.py
출력:  figures/wiring/phase1.svg
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_drawings_lib import (
  Sheet, PW, PH, MARGIN, INK, MUTE, GREEN, TINT, text_width,
)
import make_wiring_drawings as W


# ---- Phase 1 에서 쓰는 자리만 골라 온다 ----
# W.CH[0] 이 적색 채널이다. (이름, 색, 우노핀, 점퍼열, 저항끝열, 캐소드열)
R_NAME, R_COL, R_PIN, R_JUMP, R_RES, R_CATH = W.CH[0]

# Phase 2 에서 녹·청이 들어갈 자리 (지금은 비워 두는 구간)
P2_FROM, P2_TO = W.CH[1][3], W.CH[2][5]   # 11 열 ~ 26 열


# ---- 연결 확인표 11칸 ----
CHECKS = [
  ("GND", "우노 GND", "위 − 줄", W.C_GND),
  ("GND", "위 − 줄", "아래 − 줄", W.C_GND),
  ("적", "우노 D8", "2 A", W.C_R),
  ("적", "저항 220Ω", "2 C ↔ 6 C", "#a16207"),
  ("적", "적색 LED 긴 다리(+)", "6 E", W.C_R),
  ("적", "적색 LED 짧은 다리(−)", "8 E", W.C_R),
  ("적", "8 A", "위 − 줄", W.C_GND),
  ("검출", "우노 D7", "3 J", W.C_DET),
  ("검출", "검출 LED 캐소드(−, 렌즈 안 큰 컵 쪽)  ⚠", "3 G", W.C_DET),
  ("검출", "검출 LED 애노드(+)  ⚠", "5 G", W.C_DET),
  ("검출", "5 J", "아래 − 줄", W.C_GND),
]


def draw_phase1_wiring(sh, bb):
  """적색 채널 + 검출 LED + GND 만 그린다."""
  p = bb.p
  top = bb.oy - p * 1.4
  bot = bb.xy(1, "-b")[1] + p * 2.0

  # --- GND: 위 − 줄과 아래 − 줄을 왼쪽으로 돌아 잇는다 ---
  x, y = bb.xy(1, "-t")
  x2, y2 = bb.xy(1, "-b")
  sh.add('<path d="M %.2f %.2f C %.2f %.2f, %.2f %.2f, %.2f %.2f" '
         'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
         % (x, y, x - p * 3.4, y, x - p * 3.4, y2, x2, y2,
            W.C_GND, p * 0.24))
  sh.circle(x, y, p * 0.2, fill=W.C_GND, stroke="none")
  sh.circle(x2, y2, p * 0.2, fill=W.C_GND, stroke="none")
  W.lead(sh, bb, (15, "-t"), top, W.C_GND, "우노 GND")

  # --- Phase 2 에서 쓸 빈 구간 표시 ---
  bx1 = bb.xy(P2_FROM, "A")[0] - p * 0.6
  bx2 = bb.xy(P2_TO, "A")[0] + p * 0.6
  by1 = bb.xy(1, "A")[1] - p * 0.6
  by2 = bb.xy(1, "E")[1] + p * 0.6
  sh.rect(bx1, by1, bx2 - bx1, by2 - by1, fill="none", stroke="#cbd5e1",
          sw=0.35, rx=p * 0.2, dash="1.6 1.2")

  # 구멍 위에 글자가 겹치면 읽기 어려우므로 흰 바탕을 깔고 두 줄로 쓴다.
  cx = (bx1 + bx2) / 2.0
  cy = (by1 + by2) / 2.0
  size = p * 0.58
  rows = ["Phase 2 에서 녹 · 청 채널 (%d ~ %d 열)" % (P2_FROM, P2_TO),
          "지금은 비워 둡니다"]
  for i, s in enumerate(rows):
    yy = cy + (i - 0.5) * size * 1.5
    w = text_width(s, size)
    sh.rect(cx - w / 2.0 - 1.0, yy - size * 0.85, w + 2.0, size * 1.35,
            fill="#ffffff", stroke="none")
    sh.txt(cx, yy, s, size, anchor="middle", color=MUTE)

  # --- 적색 발광 채널 ---
  W.resistor(sh, bb, R_JUMP, R_RES, "C")
  W.led(sh, bb, R_RES, R_CATH, "E", R_COL, "발광 " + R_NAME)
  W.wire(sh, bb, (R_CATH, "A"), (R_CATH, "-t"), W.C_GND)
  W.lead(sh, bb, (R_JUMP, "A"), top, R_COL, "우노 " + R_PIN)

  # --- 검출 LED (아래쪽 반, 극성 반대) ---
  W.led(sh, bb, W.DET_A, W.DET_K, "G", W.C_DET, "검출 LED", flip_note=True)
  W.wire(sh, bb, (W.DET_A, "J"), (W.DET_A, "-b"), W.C_GND)
  W.lead(sh, bb, (W.DET_K, "J"), bot, W.C_DET, "우노 D7", up=False)


def sheet():
  sh = Sheet(1, "Phase 1 배선도",
             "적색 1채널 + 검출 LED — 전체 26칸 중 11칸만 꽂습니다",
             total=1, doc="Phase 1 배선도")

  sh.band(MARGIN, 25, PW - 2 * MARGIN, 20, "여기까지만 꽂습니다",
          ["Phase 1 펌웨어(02_phase1)는 DARK 와 R 두 가지만 측정합니다.",
           "녹·청 LED · 버튼 · OLED 는 코드가 건드리지 않아 지금은 꽂지 않습니다."])

  sh.txt(MARGIN, 50, "브레드보드 배치 — 열 번호는 전체 배선도와 같습니다",
         4.4, weight="700")

  bb = W.Board(39.0, 64.0, 4.4)
  W.draw_board(sh, bb)
  draw_phase1_wiring(sh, bb)

  # ---- 연결 확인표 ----
  sh.txt(MARGIN, 154, "연결 확인표 — USB 를 꽂기 전에 11칸을 전부 확인하세요",
         4.4, weight="700")
  ty = 157
  cols = [MARGIN + 2, MARGIN + 8, MARGIN + 22, MARGIN + 108, MARGIN + 168]
  sh.rect(MARGIN, ty, PW - 2 * MARGIN, 7, fill=TINT, stroke="none")
  for x, h in zip(cols[1:], ["채널", "연결하는 것", "꽂는 곳", "쓴 선 색"]):
    sh.txt(x, ty + 4.8, h, 3.0, weight="700")
  ty += 7
  for i, (ch, what, where, col) in enumerate(CHECKS):
    yy = ty + i * 5.6
    if i % 2:
      sh.rect(MARGIN, yy, PW - 2 * MARGIN, 5.6, fill="#f8fafc", stroke="none")
    sh.check(cols[0], yy + 4.0, "", 3.0)
    sh.txt(cols[1], yy + 4.0, ch, 2.9, color=MUTE)
    sh.txt(cols[2], yy + 4.0, what, 3.0,
           weight="700" if "⚠" in what else "400",
           color=W.C_DET if "⚠" in what else INK)
    sh.txt(cols[3], yy + 4.0, where, 3.0, weight="700")
    sh.circle(cols[4] + 1.6, yy + 2.9, 1.5, fill=col, stroke="none")
    sh.line(cols[4] + 5, yy + 4.4, PW - MARGIN - 2, yy + 4.4, "#cbd5e1", 0.25)

  sh.warn(MARGIN, 228, PW - 2 * MARGIN,
          "검출 LED — 이 회로에서 유일하게 거꾸로 꽂는 부품",
          ["캐소드(−) → 우노 D7,  애노드(+) → GND 입니다. 캐소드는 다리 길이보다",
           "**렌즈 안의 큰 컵**으로 판별하세요. 저항은 넣지 않습니다.",
           "색은 반드시 **적색**. 청·녹은 Red 채널이 광전류를 거의 못 만듭니다."])

  sh.band(MARGIN, 257, PW - 2 * MARGIN, 26,
          "다 꽂은 뒤 — 극성은 눈이 아니라 값으로 확인합니다",
          ["11칸을 모두 확인한 다음에 USB 를 꽂습니다.  수신 설정: **38400 bps, 8N1**.",
           "· 값이 **0~1 tick** 이면 검출 LED 가 뒤집힌 것 — 그대로 **180° 돌려** 꽂으세요.",
           "· **TIMEOUT** 이면 검출 LED 가 접속되지 않은 것 — 다리와 점퍼를 다시 꽂으세요."],
          color=GREEN)

  sh.foot("핀 배정 출처: firmware/common/pedd.c")
  return sh


def main():
  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  outdir = os.path.join(root, "figures", "wiring")
  if not os.path.isdir(outdir):
    os.makedirs(outdir)

  svg = sheet().render()
  if 'width="210mm" height="297mm"' not in svg:
    raise SystemExit("용지 크기가 A4 가 아닙니다")
  path = os.path.join(outdir, "phase1.svg")
  with io.open(path, "w", encoding="utf-8") as f:
    f.write(svg)
  print("generated: figures/wiring/phase1.svg")


if __name__ == "__main__":
  main()
