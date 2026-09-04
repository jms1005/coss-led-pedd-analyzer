# -*- coding: utf-8 -*-
"""
make_wiring_drawings.py — 브레드보드 배선도 4장 생성

회로도(`figures/fig3_schematic.svg`)는 심사 제출용이라 부품 기호로 그려져
있어 실제 브레드보드와 대응이 잘 안 된다. 이 도면은 **어느 구멍에 무엇을
꽂는지**만 그린다.

  1장  한눈에 보기 (연결 요약 + 핀 대응표 + LED 극성 판별)
  2장  브레드보드 배치도 (구멍 번호까지 지정)
  3장  연결 순서 6단계
  4장  연결 확인표 + 흔한 실수 + 첫 전원 인가

핀 배정의 출처는 펌웨어다. 바꾸려면 아래 PINS 가 아니라 펌웨어를 먼저 고칠 것.
  firmware/common/pedd.c    발광 PB0/PB1/PB2, 검출 PD7
  firmware/common/button.c  버튼 PD2 (내부 풀업)
  firmware/common/i2c.c     OLED PC4=SDA, PC5=SCL

실행:  python tools/make_wiring_drawings.py
출력:  figures/wiring/wire1.svg ... wire4.svg
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_drawings_lib import (
  Sheet, PW, PH, MARGIN, INK, MUTE, RED, BLUE, GREEN, TINT,
)

# ---- 배선 색 (실제 점퍼선 색과 맞추면 확인이 쉬워진다) ----
C_GND = "#0f172a"    # 검정 — GND
C_R = "#dc2626"      # 빨강 — 발광 R
C_G = "#16a34a"      # 초록 — 발광 G
C_B = "#2563eb"      # 파랑 — 발광 B
C_DET = "#7c3aed"    # 보라 — 검출 LED
C_BTN = "#ea580c"    # 주황 — 버튼

# ---- 핀 배정 (MCU 핀, 우노 표기, 연결 대상, 색) ----
PINS = [
  ("PB0", "D8", "발광 LED 적색 (R1 220Ω 거쳐)", C_R),
  ("PB1", "D9", "발광 LED 녹색 (R2 220Ω 거쳐)", C_G),
  ("PB2", "D10", "발광 LED 청색 (R3 220Ω 거쳐)", C_B),
  ("PD7", "D7", "검출 LED 캐소드 (짧은 다리)", C_DET),
  ("PD2", "D2", "버튼 SW1", C_BTN),
  ("PC4", "A4", "OLED SDA", INK),
  ("PC5", "A5", "OLED SCL", INK),
  ("—", "5V", "OLED VCC", INK),
  ("—", "GND", "브레드보드 GND 줄 (− 줄)", C_GND),
]

# ---- 브레드보드 행 순서와 앞쪽 여백(칸 단위) ----
ROWS = ["+t", "-t", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
        "+b", "-b"]
ROW_GAP = {"A": 0.9, "F": 1.5, "+b": 0.9}
NCOL = 30


class Board(object):
  """브레드보드 좌표 계산기. col 은 1부터, row 는 ROWS 의 이름."""

  def __init__(self, ox, oy, p):
    self.ox, self.oy, self.p = ox, oy, p

  def xy(self, col, row):
    y = self.oy
    for r in ROWS:
      y += ROW_GAP.get(r, 0) * self.p
      if r == row:
        return (self.ox + (col - 0.5) * self.p, y)
      y += self.p
    raise KeyError(row)

  @property
  def width(self):
    return NCOL * self.p

  @property
  def height(self):
    return self.xy(1, "-b")[1] - self.oy + self.p


def draw_board(sh, bb, labels=True):
  """빈 브레드보드."""
  p = bb.p
  x0, y0 = bb.ox, bb.oy - p * 0.6
  w, h = bb.width, bb.height + p * 0.2
  sh.rect(x0 - p * 0.6, y0, w + p * 1.2, h, fill="#f8fafc", stroke="#cbd5e1",
          sw=0.35, rx=p * 0.4)

  # 가운데 홈
  ey = bb.xy(1, "E")[1]
  fy = bb.xy(1, "F")[1]
  sh.rect(x0 - p * 0.6, ey + p * 0.5, w + p * 1.2, fy - ey - p,
          fill="#e2e8f0", stroke="none")

  # 전원 레일 줄
  for row, color in (("+t", "#ef4444"), ("-t", "#3b82f6"),
                     ("+b", "#ef4444"), ("-b", "#3b82f6")):
    yy = bb.xy(1, row)[1]
    sh.line(x0 - p * 0.3, yy, x0 + w + p * 0.3, yy, color, 0.25)

  # 구멍
  for ci in range(1, NCOL + 1):
    for r in ROWS:
      cx, cy = bb.xy(ci, r)
      sh.circle(cx, cy, p * 0.16, fill="#ffffff", stroke="#94a3b8", sw=0.12)

  if not labels:
    return
  for ci in range(1, NCOL + 1):
    if ci % 5 == 0 or ci == 1:
      sh.txt(bb.xy(ci, "A")[0], bb.xy(ci, "A")[1] - p * 0.6, str(ci),
             p * 0.62, anchor="middle", color=MUTE)
      sh.txt(bb.xy(ci, "J")[0], bb.xy(ci, "J")[1] + p * 1.15, str(ci),
             p * 0.62, anchor="middle", color=MUTE)
  for r in ("A", "E", "F", "J"):
    sh.txt(x0 - p * 1.1, bb.xy(1, r)[1] + p * 0.22, r, p * 0.62,
           anchor="middle", color=MUTE, weight="700")
  sh.txt(x0 - p * 1.1, bb.xy(1, "-t")[1] + p * 0.22, "−", p * 0.8,
         anchor="middle", color="#3b82f6", weight="700")
  sh.txt(x0 - p * 1.1, bb.xy(1, "-b")[1] + p * 0.22, "−", p * 0.8,
         anchor="middle", color="#3b82f6", weight="700")


def wire(sh, bb, a, b, color, sw=None, drop=None):
  """구멍 a 에서 b 로 가는 점퍼선. a, b 는 (col, row)."""
  x1, y1 = bb.xy(*a)
  x2, y2 = bb.xy(*b)
  w = sw or bb.p * 0.24
  if drop is None:
    sh.line(x1, y1, x2, y2, color, w, cap="round")
  else:
    sh.add('<path d="M %.2f %.2f C %.2f %.2f, %.2f %.2f, %.2f %.2f" '
           'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
           % (x1, y1, x1, y1 + drop, x2, y2 + drop, x2, y2, color, w))
  for (px, py) in ((x1, y1), (x2, y2)):
    sh.circle(px, py, bb.p * 0.2, fill=color, stroke="none")


def lead(sh, bb, hole, to_y, color, label, up=True):
  """보드 밖으로 나가는 점퍼 — 우노로 가는 선."""
  x, y = bb.xy(*hole)
  sh.line(x, y, x, to_y, color, bb.p * 0.24, cap="round")
  sh.circle(x, y, bb.p * 0.2, fill=color, stroke="none")
  dy = -1.2 if up else 3.0
  sh.txt(x, to_y + dy, label, bb.p * 0.72, anchor="middle", weight="700",
         color=color)


def resistor(sh, bb, c1, c2, row, label="220Ω"):
  x1, y = bb.xy(c1, row)
  x2, _ = bb.xy(c2, row)
  p = bb.p
  sh.line(x1, y, x2, y, "#a16207", p * 0.16)
  sh.rect(x1 + p * 0.8, y - p * 0.38, (x2 - x1) - p * 1.6, p * 0.76,
          fill="#fde68a", stroke="#a16207", sw=0.3, rx=p * 0.15)
  for k in (0.3, 0.5, 0.7):
    bx = x1 + p * 0.8 + ((x2 - x1) - p * 1.6) * k
    sh.line(bx, y - p * 0.38, bx, y + p * 0.38, "#a16207", p * 0.1)
  for (px) in (x1, x2):
    sh.circle(px, y, p * 0.2, fill="#a16207", stroke="none")
  sh.txt((x1 + x2) / 2.0, y - p * 0.72, label, p * 0.66, anchor="middle",
         color="#a16207", weight="700")


def led(sh, bb, c_anode, c_cathode, row, color, label, flip_note=False):
  """LED. 애노드(긴 다리)와 캐소드(짧은 다리) 구멍을 각각 받는다."""
  p = bb.p
  xa, y = bb.xy(c_anode, row)
  xk, _ = bb.xy(c_cathode, row)
  mid = (xa + xk) / 2.0
  sh.line(xa, y, xk, y, "#94a3b8", p * 0.16)
  sh.circle(mid, y - p * 0.1, p * 0.62, fill=color, stroke=INK, sw=0.3)
  sh.circle(xa, y, p * 0.22, fill=INK, stroke="none")
  sh.circle(xk, y, p * 0.22, fill="#ffffff", stroke=INK, sw=0.28)
  sh.txt(xa, y + p * 1.25, "+", p * 0.85, anchor="middle", weight="700",
         color=INK)
  sh.txt(xk, y + p * 1.25, "−", p * 0.85, anchor="middle", weight="700",
         color=RED if flip_note else INK)
  sh.txt(mid, y - p * 1.05, label, p * 0.66, anchor="middle", weight="700",
         color=color if not flip_note else RED)


# ---- 부품이 꽂히는 자리 (한 곳에 모아 둔다) ----
# 열 번호는 1부터. 위쪽 반(A~E)과 아래쪽 반(F~J)은 같은 열이라도 서로 이어져
# 있지 않다. 그래서 위쪽 20열과 아래쪽 20열을 따로 쓸 수 있다.
CH = [
  ("R", C_R, "D8", 2, 6, 8),     # (이름, 색, 우노핀, 점퍼열, 저항끝열, 캐소드열)
  ("G", C_G, "D9", 11, 15, 17),
  ("B", C_B, "D10", 20, 24, 26),
]
DET_K, DET_A = 3, 5        # 검출 LED 캐소드 / 애노드 열 (아래쪽 반)
SW_C1, SW_C2 = 28, 30      # 버튼이 중앙 홈을 가로지르는 두 열


def draw_wiring(sh, bb, steps, leads_on=True):
  """steps 에 든 단계의 부품·배선만 그린다. 1~6."""
  p = bb.p
  top = bb.oy - p * 1.4
  bot = bb.xy(1, "-b")[1] + p * 2.0

  if 1 in steps:                      # GND 레일
    x, y = bb.xy(1, "-t")
    x2, y2 = bb.xy(1, "-b")
    sh.add('<path d="M %.2f %.2f C %.2f %.2f, %.2f %.2f, %.2f %.2f" '
           'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round"/>'
           % (x, y, x - p * 3.4, y, x - p * 3.4, y2, x2, y2,
              C_GND, p * 0.24))
    sh.circle(x, y, p * 0.2, fill=C_GND, stroke="none")
    sh.circle(x2, y2, p * 0.2, fill=C_GND, stroke="none")
    if leads_on:
      lead(sh, bb, (15, "-t"), top, C_GND, "우노 GND")

  for i, (nm, col, pin, c_j, c_r, c_k) in enumerate(CH):
    if 2 in steps:
      resistor(sh, bb, c_j, c_r, "C")
    if 3 in steps:
      led(sh, bb, c_r, c_k, "E", col, "발광 " + nm)
      wire(sh, bb, (c_k, "A"), (c_k, "-t"), C_GND)
    if 3 in steps and leads_on:
      lead(sh, bb, (c_j, "A"), top, col, "우노 " + pin)

  if 4 in steps:
    led(sh, bb, DET_A, DET_K, "G", C_DET, "검출 LED", flip_note=True)
    wire(sh, bb, (DET_A, "J"), (DET_A, "-b"), C_GND)
    if leads_on:
      lead(sh, bb, (DET_K, "J"), bot, C_DET, "우노 D7", up=False)

  if 5 in steps:
    x1, y1 = bb.xy(SW_C1, "E")
    x2, y2 = bb.xy(SW_C2, "F")
    sh.rect(x1 - p * 0.55, y1 - p * 0.55, (x2 - x1) + p * 1.1,
            (y2 - y1) + p * 1.1, fill="#e2e8f0", stroke=INK, sw=0.35,
            rx=p * 0.2)
    for (cc, rr) in ((SW_C1, "E"), (SW_C2, "E"), (SW_C1, "F"), (SW_C2, "F")):
      hx, hy = bb.xy(cc, rr)
      sh.circle(hx, hy, p * 0.2, fill=INK, stroke="none")
    sh.txt((x1 + x2) / 2.0, y1 - p * 1.1, "버튼 SW1", p * 0.66,
           anchor="middle", weight="700", color=C_BTN)
    wire(sh, bb, (SW_C2, "J"), (SW_C2, "-b"), C_GND)
    if leads_on:
      lead(sh, bb, (SW_C1, "A"), top, C_BTN, "우노 D2")


# ============================ 1장 ============================

def wire1():
  sh = Sheet(1, "① 한눈에 보기",
             "무엇을 어디에 연결하는지 — 먼저 이 장을 읽으세요", total=4,
             doc="브레드보드 배선도")

  sh.band(MARGIN, 25, PW - 2 * MARGIN, 26, "이 회로가 하는 일",
          ["우노가 발광 LED 3개를 하나씩 켜서 시료에 빛을 보내고, 반대편 검출 LED 로",
           "그 빛을 받습니다. 버튼으로 측정을 시작하고 결과는 OLED 화면에 나옵니다."])

  # ---- 블록 연결도 ----
  bx, by, bw, bh = MARGIN + 6, 58, 46, 16
  sh.rect(bx, by, bw, bh, fill="#e0e7ff", stroke=INK, sw=0.4, rx=2)
  sh.txt(bx + bw / 2.0, by + 7, "Arduino Uno", 4.0, anchor="middle",
         weight="700")
  sh.txt(bx + bw / 2.0, by + 12, "ATmega328P", 2.8, anchor="middle",
         color=MUTE)

  targets = [
    ("발광 LED 적 · 녹 · 청", "D8 · D9 · D10", C_R, 0),
    ("검출 LED (거꾸로!)", "D7", C_DET, 1),
    ("버튼 SW1", "D2", C_BTN, 2),
    ("OLED 화면", "A4 · A5 · 5V · GND", INK, 3),
  ]
  for name, pin, col, i in targets:
    ty = 56 + i * 17
    tx = 120
    sh.rect(tx, ty, 62, 13, fill="#ffffff", stroke=col, sw=0.5, rx=2)
    sh.txt(tx + 4, ty + 5.6, name, 3.4, weight="700", color=col)
    sh.txt(tx + 4, ty + 10.2, pin, 2.9, color=MUTE)
    sh.add('<path d="M %.2f %.2f C %.2f %.2f, %.2f %.2f, %.2f %.2f" '
           'fill="none" stroke="%s" stroke-width="0.8" stroke-linecap="round"/>'
           % (bx + bw, by + bh / 2.0, bx + bw + 30, by + bh / 2.0,
              tx - 30, ty + 6.5, tx, ty + 6.5, col))

  # ---- 핀 대응표 ----
  ty = 132
  sh.txt(MARGIN, ty, "핀 대응표 — 우노 보드에 적힌 번호를 보세요", 4.4,
         weight="700")
  ty += 6
  cols = [MARGIN + 2, MARGIN + 30, MARGIN + 56, MARGIN + 150]
  sh.rect(MARGIN, ty, PW - 2 * MARGIN, 7, fill=TINT, stroke="none")
  for x, h in zip(cols, ["MCU 핀", "우노 표기", "연결 대상", "점퍼선 색"]):
    sh.txt(x, ty + 4.8, h, 3.1, weight="700")
  ty += 7
  names = {C_R: "빨강", C_G: "초록", C_B: "파랑", C_DET: "보라",
           C_BTN: "주황", C_GND: "검정", INK: "아무 색"}
  for i, (mcu, uno, what, col) in enumerate(PINS):
    yy = ty + i * 6.4
    if i % 2:
      sh.rect(MARGIN, yy, PW - 2 * MARGIN, 6.4, fill="#f8fafc", stroke="none")
    sh.txt(cols[0], yy + 4.4, mcu, 3.0, color=MUTE)
    sh.txt(cols[1], yy + 4.4, uno, 3.2, weight="700")
    sh.txt(cols[2], yy + 4.4, what, 3.0)
    sh.circle(cols[3] + 1.6, yy + 3.3, 1.5, fill=col, stroke="none")
    sh.txt(cols[3] + 5, yy + 4.4, names.get(col, ""), 3.0, color=MUTE)
  ty += len(PINS) * 6.4 + 6

  # ---- LED 극성 ----
  sh.txt(MARGIN, ty, "LED 다리 구별하는 법", 4.4, weight="700")
  ty += 5
  sh.band(MARGIN, ty, 96, 40, "긴 다리 = + , 짧은 다리 = −",
          ["LED 를 옆에서 보면 다리 길이가 다릅니다.",
           "짧은 다리 쪽 렌즈 테두리가 평평하게",
           "깎여 있기도 합니다.",
           "",
           "· 긴 다리(+, 애노드) → 저항 쪽",
           "· 짧은 다리(−, 캐소드) → GND 쪽"], color=GREEN, lead=4.2)

  sh.warn(PW / 2.0 + 4, ty, PW / 2.0 - MARGIN - 4,
          "검출 LED 하나만 반대입니다",
          ["발광 LED 3개는 짧은 다리가 GND 로 갑니다. 보통 방식입니다.",
           "",
           "검출 LED(D4)만 **짧은 다리가 우노 D7 로**, 긴 다리가 GND 로",
           "갑니다. 거꾸로 꽂아야 빛을 받아 전기를 만드는 소자가 됩니다.",
           "",
           "이걸 바로 꽂으면 측정이 전부 TIMEOUT 으로 나옵니다."])
  sh.foot("핀 배정 출처: firmware/common/pedd.c · button.c · i2c.c")
  return sh


# ============================ 2장 ============================

def wire2():
  sh = Sheet(2, "② 브레드보드 배치도",
             "구멍 번호를 보고 그대로 꽂으세요", total=4,
             doc="브레드보드 배선도")

  sh.warn(MARGIN, 25, PW - 2 * MARGIN, "이 그림은 실제 크기가 아닙니다",
          ["차광 챔버 도면과 달리 이 장은 대고 자르는 템플릿이 아닙니다.",
           "구멍의 번호(가로 1~30)와 줄 이름(세로 A~J)을 보고 꽂으세요."])

  sh.band(MARGIN, 52, PW - 2 * MARGIN, 33, "브레드보드가 이어지는 방향",
          ["· 세로로 A~E 다섯 구멍이 한 덩어리, F~J 다섯 구멍이 또 한 덩어리입니다.",
           "· 가운데 홈을 사이에 두고 위아래는 **서로 이어져 있지 않습니다.**",
           "· 맨 위·맨 아래의 − 줄은 가로로 쭉 이어집니다. 여기가 GND 입니다.",
           "· **− 줄이 가운데서 끊어진 제품이 있습니다.** 파란 선이 중간에 끊겨 있으면",
           "  끊긴 두 구간을 점퍼선으로 이어주세요. 안 그러면 오른쪽 절반이 죽습니다."])

  bb = Board(40.0, 103.0, 4.3)
  draw_board(sh, bb)
  draw_wiring(sh, bb, {1, 2, 3, 4, 5})

  sh.txt(PW / 2.0, 192,
         "※ 우노에서 오는 점퍼선은 전원 줄 위를 지나갑니다. 닿아도 상관없습니다.",
         2.9, anchor="middle", color=MUTE, italic=True)

  sh.band(MARGIN, 198, PW - 2 * MARGIN, 44, "그림 읽는 법",
          ["· 노란 몸통 = 저항 220Ω.  동그란 색 = LED.  회색 네모 = 버튼.",
           "· LED 아래의 + 는 긴 다리, − 는 짧은 다리를 꽂는 구멍입니다.",
           "· 검은 선은 전부 GND 로 가는 선입니다.",
           "· 왼쪽 바깥으로 도는 검은 선은 위 − 줄과 아래 − 줄을 잇는 선입니다.",
           "  검출 LED 와 버튼이 아래쪽 반에 있어서 아래 − 줄도 살려야 합니다.",
           "",
           "OLED 는 브레드보드를 거치지 않고 우노에 직접 4선으로 꽂습니다 (1장 표)."])

  sh.warn(MARGIN, 248, PW - 2 * MARGIN, "가장 많이 틀리는 곳",
          ["검출 LED(보라색 선) 는 **짧은 다리가 D7**, 긴 다리가 GND 입니다. 반대로 꽂지 마세요.",
           "버튼은 가운데 홈을 가로질러 꽂고, **대각선으로 마주 보는 두 다리**를 씁니다.",
           "대각선 두 다리는 눌러야만 이어지므로, 방향을 몰라도 항상 맞습니다."])
  sh.foot("배선도 · 실제 크기 아님")
  return sh


# ============================ 3장 ============================

STEPS = [
  ("GND 줄부터 만들기",
   ["우노 GND → 브레드보드 위 − 줄에 꽂습니다.",
    "위 − 줄과 아래 − 줄을 선 하나로 잇습니다.",
    "GND 는 모든 부품이 함께 쓰는 기준점입니다."], {1}),
  ("저항 3개 꽂기",
   ["220Ω 저항 3개를 C 줄에 나란히 꽂습니다.",
    "2↔6, 11↔15, 20↔24 열입니다.",
    "저항은 방향이 없어서 아무렇게나 꽂아도 됩니다."], {1, 2}),
  ("발광 LED 3개 꽂기",
   ["긴 다리(+)를 저항 쪽, 짧은 다리(−)를 오른쪽에.",
    "짧은 다리 열에서 위 − 줄로 검은 선을 놓습니다.",
    "우노 D8·D9·D10 을 각 저항 왼쪽 열에 꽂습니다."], {1, 2, 3}),
  ("검출 LED 꽂기 — 거꾸로!",
   ["아래쪽 반(G 줄)에 꽂습니다.",
    "짧은 다리(−)가 3열, 긴 다리(+)가 5열입니다.",
    "3열 → 우노 D7, 5열 → 아래 − 줄."], {1, 2, 3, 4}),
  ("버튼 꽂기",
   ["가운데 홈을 가로질러 28·30 열에 꽂습니다.",
    "대각선 두 다리만 씁니다: 28열 위 → 우노 D2,",
    "30열 아래 → 아래 − 줄."], {1, 2, 3, 4, 5}),
]


def wire3():
  sh = Sheet(3, "③ 연결 순서",
             "위에서 아래로 하나씩. 다 꽂고 나서 4장으로 확인하세요", total=4,
             doc="브레드보드 배선도")

  x0, y0 = MARGIN, 26.0
  cw, ch = (PW - 2 * MARGIN) / 2.0, 62.0
  for i, (title, body, steps) in enumerate(STEPS):
    cx = x0 + (i % 2) * cw
    cy = y0 + (i // 2) * ch
    sh.rect(cx, cy, cw - 4, ch - 4, fill="#ffffff", stroke="#e2e8f0",
            sw=0.35, rx=2)
    sh.step_no(cx + 8, cy + 8, i + 1)
    sh.txt(cx + 14, cy + 9.4, title, 4.0, weight="700")
    sh.lines(cx + 14, cy + 16, body, 2.85, 4.0)
    bb = Board(cx + 17, cy + 28, 1.7)
    draw_board(sh, bb, labels=False)
    draw_wiring(sh, bb, steps, leads_on=False)

  # 6번 — OLED 는 브레드보드를 거치지 않는다
  cx, cy = x0 + cw, y0 + 2 * ch
  sh.rect(cx, cy, cw - 4, ch - 4, fill="#ffffff", stroke="#e2e8f0", sw=0.35,
          rx=2)
  sh.step_no(cx + 8, cy + 8, 6)
  sh.txt(cx + 14, cy + 9.4, "OLED 화면 연결", 4.0, weight="700")
  sh.lines(cx + 14, cy + 16,
           ["브레드보드를 거치지 않고 우노에 직접 꽂습니다.",
            "암-수(F-M) 점퍼선 4개를 씁니다."], 2.85, 4.0)
  ox, oy = cx + 14, cy + 28
  sh.rect(ox, oy, 30, 16, fill="#1e293b", stroke=INK, sw=0.4, rx=1)
  sh.txt(ox + 15, oy + 9, "OLED", 3.4, anchor="middle", weight="700",
         color="#ffffff")
  for k, (nm, dst) in enumerate((("VCC", "5V"), ("GND", "GND"),
                                 ("SDA", "A4"), ("SCL", "A5"))):
    yy = oy + 20 + k * 5.4
    sh.line(ox + 4, oy + 16, ox + 4, yy, INK, 0.4)
    sh.line(ox + 4, yy, ox + 16, yy, INK, 0.4)
    sh.txt(ox + 18, yy + 1.1, "%s  →  우노 %s" % (nm, dst), 3.0,
           weight="700")

  sh.warn(MARGIN, 224, PW - 2 * MARGIN, "다 꽂기 전에는 USB 를 연결하지 마세요",
          ["배선 중에 전원이 들어가 있으면 잘못 닿았을 때 우노가 상할 수 있습니다.",
           "6단계까지 끝내고 4장의 확인표를 모두 통과한 뒤에 USB 를 꽂습니다."])

  sh.band(MARGIN, 252, PW - 2 * MARGIN, 30, "점퍼선이 모자라면",
          ["색을 꼭 맞출 필요는 없습니다. 다만 **GND 는 검은색으로 통일**하세요.",
           "나중에 잘못된 곳을 찾을 때 검은 선만 눈으로 훑으면 되기 때문입니다.",
           "어떤 색을 어디에 썼는지 4장 표의 빈칸에 적어두면 더 좋습니다."],
          color=GREEN)
  sh.foot("연결 순서")
  return sh


# ============================ 4장 ============================

CHECKS = [
  ("GND", "우노 GND", "위 − 줄", C_GND),
  ("GND", "위 − 줄", "아래 − 줄", C_GND),
  ("적", "우노 D8", "2 A", C_R),
  ("적", "저항 220Ω", "2 C ↔ 6 C", "#a16207"),
  ("적", "적색 LED 긴 다리(+)", "6 E", C_R),
  ("적", "적색 LED 짧은 다리(−)", "8 E", C_R),
  ("적", "8 A", "위 − 줄", C_GND),
  ("녹", "우노 D9", "11 A", C_G),
  ("녹", "저항 220Ω", "11 C ↔ 15 C", "#a16207"),
  ("녹", "녹색 LED 긴 다리(+)", "15 E", C_G),
  ("녹", "녹색 LED 짧은 다리(−)", "17 E", C_G),
  ("녹", "17 A", "위 − 줄", C_GND),
  ("청", "우노 D10", "20 A", C_B),
  ("청", "저항 220Ω", "20 C ↔ 24 C", "#a16207"),
  ("청", "청색 LED 긴 다리(+)", "24 E", C_B),
  ("청", "청색 LED 짧은 다리(−)", "26 E", C_B),
  ("청", "26 A", "위 − 줄", C_GND),
  ("검출", "우노 D7", "3 J", C_DET),
  ("검출", "검출 LED 짧은 다리(−)  ⚠", "3 G", C_DET),
  ("검출", "검출 LED 긴 다리(+)  ⚠", "5 G", C_DET),
  ("검출", "5 J", "아래 − 줄", C_GND),
  ("버튼", "버튼 SW1 (가운데 홈 가로질러)", "28·30 열 E·F", C_BTN),
  ("버튼", "우노 D2", "28 A", C_BTN),
  ("버튼", "30 J", "아래 − 줄", C_GND),
  ("OLED", "VCC / GND", "우노 5V / GND", INK),
  ("OLED", "SDA / SCL", "우노 A4 / A5", INK),
]


def wire4():
  sh = Sheet(4, "④ 연결 확인표", "USB 를 꽂기 전에 26칸을 전부 확인하세요",
             total=4, doc="브레드보드 배선도")

  ty = 27
  cols = [MARGIN + 2, MARGIN + 8, MARGIN + 22, MARGIN + 108, MARGIN + 168]
  sh.rect(MARGIN, ty, PW - 2 * MARGIN, 7, fill=TINT, stroke="none")
  for x, h in zip(cols[1:], ["채널", "연결하는 것", "꽂는 곳", "쓴 선 색"]):
    sh.txt(x, ty + 4.8, h, 3.0, weight="700")
  ty += 7
  for i, (ch, what, where, col) in enumerate(CHECKS):
    yy = ty + i * 6.0
    if i % 2:
      sh.rect(MARGIN, yy, PW - 2 * MARGIN, 6.0, fill="#f8fafc", stroke="none")
    sh.check(cols[0], yy + 4.2, "", 3.0)
    sh.txt(cols[1], yy + 4.2, ch, 2.9, color=MUTE)
    warn_row = "⚠" in what
    sh.txt(cols[2], yy + 4.2, what, 3.0, weight="700" if warn_row else "400",
           color=RED if warn_row else INK)
    sh.txt(cols[3], yy + 4.2, where, 3.0, weight="700")
    sh.circle(cols[4] + 1.4, yy + 3.2, 1.3, fill=col, stroke="none")
    sh.line(cols[4] + 5, yy + 4.6, cols[4] + 24, yy + 4.6, "#cbd5e1", 0.25)
  ty += len(CHECKS) * 6.0 + 6

  sh.warn(MARGIN, ty, PW - 2 * MARGIN, "USB 를 꽂기 직전에 이 세 가지",
          ["① 검출 LED 의 짧은 다리가 D7 인가 — 발광 LED 3개와 반대 방향입니다.",
           "② 5V 와 GND 가 어디에서도 직접 맞닿아 있지 않은가 (합선).",
           "③ 부품 다리끼리 서로 닿아 있지 않은가. 특히 LED 두 다리."])
  ty += 12 + 3 * 4.4 + 6

  sh.band(MARGIN, ty, PW - 2 * MARGIN, 40, "잘 안 될 때 어디부터 보나",
          ["· 전 채널 TIMEOUT  →  검출 LED 방향. 열에 하나는 이것입니다.",
           "· 특정 색만 TIMEOUT  →  그 색 LED 의 긴/짧은 다리, 저항 연결.",
           "· 버튼을 눌러도 반응 없음  →  대각선 두 다리를 썼는지.",
           "· OLED 화면이 안 켜짐  →  SDA·SCL 이 바뀌었는지, 주소가 0x3C 인지.",
           "· 아무것도 안 됨  →  GND 가 우노와 브레드보드에 이어져 있는지."],
          color=GREEN, lead=4.2)
  sh.foot("확인표 · 배선도 4장 끝")
  return sh


# ============================ 실행 ============================

def main():
  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  outdir = os.path.join(root, "figures", "wiring")
  if not os.path.isdir(outdir):
    os.makedirs(outdir)

  for i, fn in enumerate((wire1, wire2, wire3, wire4), 1):
    sh = fn()
    svg = sh.render()
    if 'width="210mm" height="297mm"' not in svg:
      raise SystemExit("%d장: 용지 크기가 A4 가 아닙니다" % i)
    with io.open(os.path.join(outdir, "wire%d.svg" % i), "w",
                 encoding="utf-8") as f:
      f.write(svg)
    print("생성: figures/wiring/wire%d.svg" % i)


if __name__ == "__main__":
  main()
