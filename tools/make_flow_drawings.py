# -*- coding: utf-8 -*-
"""
make_flow_drawings.py — "전기가 어디서 시작해 어떻게 흐르는가" 설명 그림 생성

`docs/쉬운_설명.md` 에 넣는 그림이다. 배선도(figures/wiring)가 **어느 구멍에
꽂는지**를 알려준다면, 이 그림은 **왜 그렇게 꽂는지**를 알려준다.

  flow1.svg  발광 LED 회로 — 전기가 도는 한 바퀴
  flow2.svg  검출 LED — 충전과 방전 2단계 (측정의 핵심)
  flow3.svg  빛과 정보의 흐름 — 전체 시스템

배선도와 달리 인쇄용 A4 가 아니라 **화면에서 읽는 가로 그림**이다. 그래서
build_drawings_lib 의 Sheet(A4 틀) 는 쓰지 않고 색과 글꼴만 공유한다.

핀 배정의 출처는 펌웨어다. 바꾸려면 여기가 아니라 펌웨어를 먼저 고칠 것.
  firmware/common/pedd.c  발광 PB0/PB1/PB2(D8/D9/D10), 검출 PD7(D7)

실행:  python tools/make_flow_drawings.py
출력:  figures/flow/flow1.svg ... flow3.svg

문서(docs/쉬운_설명.md)가 참조하는 것은 SVG 가 아니라 PNG 다. GitHub 가
마크다운 안의 SVG 를 보여줄 때 글꼴이 바뀔 수 있기 때문이다. PNG 까지
만들려면 `sh tools/make_flow_png.sh` 를 쓴다 (이 스크립트를 먼저 실행한다).
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_drawings_lib import FONT, INK, MUTE, RED, BLUE, GREEN, TINT, esc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "figures", "flow")

# ---- 색 (배선도와 같은 값을 쓴다) ----
C_GND = "#0f172a"     # 검정 — GND
C_R = "#dc2626"       # 빨강 — 발광 R
C_DET = "#7c3aed"     # 보라 — 검출 LED
C_PWR = "#ea580c"     # 주황 — 전원(+)
C_LIGHT = "#f59e0b"   # 노랑 — 빛
PAPER = "#ffffff"
PANEL = "#f8fafc"
EDGE = "#cbd5e1"


class Canvas(object):
  """화면용 가로 그림 한 장. 좌표 단위는 px."""

  def __init__(self, w, h, title, subtitle=""):
    self.w, self.h = w, h
    self.el = []
    self.txt(40, 42, title, 21, weight="700")
    if subtitle:
      self.txt(40, 66, subtitle, 13, color=MUTE)

  # --- 기본 도형 ---

  def add(self, s):
    self.el.append(s)

  def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1.2, rx=0, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" '
             'fill="%s" stroke="%s" stroke-width="%.1f"%s/>'
             % (x, y, w, h, rx, fill, stroke, sw, d))

  def line(self, x1, y1, x2, y2, stroke=INK, sw=1.2, dash=None, cap="round"):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
             'stroke-width="%.1f" stroke-linecap="%s"%s/>'
             % (x1, y1, x2, y2, stroke, sw, cap, d))

  def path(self, d, stroke=INK, sw=1.2, fill="none", dash=None, cap="round"):
    da = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<path d="%s" fill="%s" stroke="%s" stroke-width="%.1f" '
             'stroke-linecap="%s" stroke-linejoin="round"%s/>'
             % (d, fill, stroke, sw, cap, da))

  def circle(self, cx, cy, r, fill="none", stroke=INK, sw=1.2, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
             'stroke-width="%.1f"%s/>' % (cx, cy, r, fill, stroke, sw, d))

  def poly(self, pts, fill="none", stroke=INK, sw=1.2):
    s = " ".join("%.1f,%.1f" % p for p in pts)
    self.add('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%.1f" '
             'stroke-linejoin="round"/>' % (s, fill, stroke, sw))

  def txt(self, x, y, s, size=13, anchor="start", weight="400", color=INK):
    """**별표로 감싼 부분**은 굵은 글씨로 나간다."""
    if "**" in s:
      body = "".join(
        ('<tspan font-weight="700">%s</tspan>' % esc(t)) if i % 2 else esc(t)
        for i, t in enumerate(s.split("**")))
    else:
      body = esc(s)
    self.add('<text x="%.1f" y="%.1f" font-size="%.1f" text-anchor="%s" '
             'font-weight="%s" fill="%s">%s</text>'
             % (x, y, size, anchor, weight, color, body))

  def lines(self, x, y, rows, size=13, lead=19, anchor="start",
            weight="400", color=INK):
    for i, r in enumerate(rows):
      self.txt(x, y + i * lead, r, size, anchor, weight, color)
    return y + (len(rows) - 1) * lead

  # --- 조합 요소 ---

  def panel(self, x, y, w, h, title=None, fill=PANEL, stroke=EDGE):
    self.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.2, rx=10)
    if title:
      self.txt(x + 16, y + 26, title, 14, weight="700")

  def badge(self, cx, cy, n, color=BLUE, r=13):
    """길 위에 얹는 번호 동그라미."""
    self.circle(cx, cy, r, fill=color, stroke=PAPER, sw=2.0)
    self.txt(cx, cy + 5, str(n), 14, anchor="middle", weight="700",
             color=PAPER)

  def arrow_head(self, x, y, ang, color=BLUE, s=7.0):
    """(x, y) 에 ang 방향(도)으로 삼각 화살촉."""
    import math
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(x, y),
           (x - s * ca + s * 0.55 * sa, y - s * sa - s * 0.55 * ca),
           (x - s * ca - s * 0.55 * sa, y - s * sa + s * 0.55 * ca)]
    self.poly(pts, fill=color, stroke=color, sw=0.5)

  def flow_arrows(self, pts, color=BLUE, sw=3.2, every=True):
    """꺾은선을 그리고 각 구간 가운데에 진행 방향 화살촉을 얹는다."""
    import math
    for i in range(len(pts) - 1):
      (x1, y1), (x2, y2) = pts[i], pts[i + 1]
      self.line(x1, y1, x2, y2, color, sw)
      if every:
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
        self.arrow_head(mx, my, ang, color)

  def resistor(self, x, y, w=64, h=17, color=INK, label=None):
    """지그재그 저항 기호. (x, y) 는 왼쪽 끝 중심."""
    n = 6
    step = w / float(n)
    d = "M %.1f %.1f" % (x, y)
    for i in range(n):
      d += " L %.1f %.1f" % (x + step * (i + 0.5),
                             y + (h / 2.0 if i % 2 == 0 else -h / 2.0))
    d += " L %.1f %.1f" % (x + w, y)
    self.path(d, stroke=color, sw=2.4)
    if label:
      self.txt(x + w / 2.0, y - 16, label, 12.5, anchor="middle",
               weight="700", color=color)

  def led(self, x, y, color, flip=False, size=20, glow=False):
    """LED 기호. 기본은 애노드(왼쪽) -> 캐소드(오른쪽).
       flip=True 면 좌우가 뒤집혀 캐소드가 왼쪽으로 온다."""
    s = size
    if not flip:
      tri = [(x, y - s * 0.62), (x, y + s * 0.62), (x + s * 0.95, y)]
      bar_x = x + s * 0.95
    else:
      tri = [(x + s * 0.95, y - s * 0.62), (x + s * 0.95, y + s * 0.62),
             (x, y)]
      bar_x = x
    self.poly(tri, fill=color, stroke=color, sw=1.4)
    self.line(bar_x, y - s * 0.72, bar_x, y + s * 0.72, color, 3.4)
    if glow:
      for k, ang in enumerate((-52, -25, 2)):
        import math
        a = math.radians(ang)
        gx = x + s * 0.5 + math.cos(a) * (s * 0.95)
        gy = y - s * 0.55 + math.sin(a) * (s * 0.95)
        self.line(x + s * 0.5 + math.cos(a) * s * 0.55,
                  y - s * 0.55 + math.sin(a) * s * 0.55,
                  gx, gy, C_LIGHT, 2.6)
    return bar_x

  def note(self, x, y, w, rows, color=BLUE, title=None, size=12.5, lead=17):
    """옅은 배경의 설명 상자. 반환: 상자 높이."""
    pad = 13
    n = len(rows) + (1 if title else 0)
    h = pad * 2 + n * lead - (lead - 13)
    self.rect(x, y, w, h, fill=TINT, stroke="none", sw=0, rx=8)
    self.line(x, y + 4, x, y + h - 4, color, 3.0)
    ty = y + pad + 11
    if title:
      self.txt(x + pad + 6, ty, title, 13, weight="700", color=color)
      ty += lead
    self.lines(x + pad + 6, ty, rows, size, lead)
    return h

  def render(self):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" font-family="%s">\n'
            '<rect width="%d" height="%d" fill="%s"/>\n%s\n</svg>\n'
            % (self.w, self.h, self.w, self.h, FONT,
               self.w, self.h, PAPER, "\n".join(self.el)))


def save(name, cv):
  p = os.path.normpath(os.path.join(OUT, name))
  with io.open(p, "w", encoding="utf-8") as f:
    f.write(cv.render())
  print("생성: figures/flow/%s" % name)


import math


def gnd_rail(cv, x1, x2, y, label="GND (− 줄)"):
  """접지 줄. 모든 전기가 돌아오는 길."""
  cv.line(x1, y, x2, y, C_GND, 4.0)
  cv.txt(x2 + 10, y + 5, label, 12.5, weight="700", color=C_GND)


def gnd_symbol(cv, x, y, color=C_GND):
  """접지 기호 (짧아지는 가로선 3개)."""
  for i, w in enumerate((11, 7, 3.5)):
    cv.line(x - w, y + i * 4.5, x + w, y + i * 4.5, color, 2.6)


def pin_box(cv, x, y, w, h, name, sub, color, dash=None):
  """보드의 핀 하나를 나타내는 상자."""
  cv.rect(x, y, w, h, fill=PAPER, stroke=color, sw=2.0, rx=6, dash=dash)
  cv.txt(x + w / 2.0, y + h / 2.0 - 2, name, 15, anchor="middle",
         weight="700", color=color)
  cv.txt(x + w / 2.0, y + h / 2.0 + 15, sub, 11.5, anchor="middle",
         color=MUTE)


def cup(cv, x, y, w, h, level, color, holes=0, drip=0):
  """물컵 비유. level 은 0~1 (찬 정도), holes 는 옆구멍 개수."""
  cv.rect(x, y, w, h, fill=PAPER, stroke=EDGE, sw=1.6, rx=4)
  fh = h * level
  if fh > 2:
    cv.rect(x + 2.5, y + h - fh, w - 5, fh - 2.5, fill=color, stroke="none",
            sw=0, rx=3)
  for i in range(holes):
    hy = y + h - fh + 8 + i * 17
    cv.circle(x + w - 1, hy, 3.2, fill=PAPER, stroke=color, sw=1.6)
    for k in range(drip):
      cv.circle(x + w + 11 + k * 12, hy + 5 + k * 7, 2.4, fill=color,
                stroke="none", sw=0)


# =========================== 1장 · 발광 회로 ===========================

def sheet1():
  cv = Canvas(1020, 580,
              "전기는 어디서 시작해 어디로 가나 — 빛을 내는 LED",
              "전기는 반드시 한 바퀴를 돌아야 흐른다. 출발점은 USB, 도착점도 USB 다.")

  # --- USB 전원 ---
  cv.rect(40, 130, 112, 86, fill=PAPER, stroke=C_PWR, sw=2.0, rx=8)
  cv.txt(96, 165, "USB 케이블", 13.5, anchor="middle", weight="700",
         color=C_PWR)
  cv.txt(96, 190, "5V", 19, anchor="middle", weight="700", color=C_PWR)
  cv.badge(40, 130, 1, C_PWR)
  cv.flow_arrows([(152, 173), (196, 173)], C_PWR, 3.4)

  # --- 우노 보드 ---
  cv.panel(196, 110, 218, 218, "아두이노 우노 보드")
  cv.rect(228, 158, 154, 78, fill=PAPER, stroke=INK, sw=1.6, rx=6)
  cv.txt(305, 190, "ATmega328P", 14, anchor="middle", weight="700")
  cv.txt(305, 210, "두뇌 칩", 12, anchor="middle", color=MUTE)
  cv.txt(305, 228, "여기가 핀을 켜고 끈다", 11, anchor="middle", color=MUTE)

  # 핀 두 개 (나가는 문 D8, 돌아오는 문 GND)
  pin_box(cv, 382, 256, 64, 36, "D8", "나가는 문", C_R)
  pin_box(cv, 382, 382, 64, 36, "GND", "돌아오는 문", C_GND)

  # --- 전기가 도는 길 ---
  Y = 274            # 나가는 길 높이
  YG = 400           # 돌아오는 길(GND 줄) 높이

  cv.badge(468, Y, 2, C_R)
  cv.flow_arrows([(446, Y), (516, Y)], C_R, 3.4)

  cv.resistor(516, Y, 68, 18, C_R, "220Ω 저항")
  cv.badge(550, Y - 42, 3, C_R)
  cv.flow_arrows([(584, Y), (650, Y)], C_R, 3.4)

  bar = cv.led(650, Y, C_R, flip=False, size=24, glow=True)
  cv.badge(706, Y - 48, 4, C_R)
  cv.txt(646, Y + 44, "긴 다리", 11.5, anchor="middle", color=MUTE)
  cv.txt(686, Y + 44, "→", 11.5, anchor="middle", color=MUTE)
  cv.txt(722, Y + 44, "짧은 다리", 11.5, anchor="middle", color=MUTE)
  cv.txt(672, Y - 66, "빨간 LED", 12.5, anchor="middle", weight="700",
         color=C_R)

  cv.flow_arrows([(bar, Y), (790, Y), (790, YG)], C_R, 3.4)

  # --- GND 줄 (돌아오는 길) ---
  gnd_rail(cv, 446, 790, YG)
  cv.flow_arrows([(700, YG), (470, YG)], C_GND, 3.4)
  cv.badge(600, YG, 5, C_GND)

  # 나머지 두 색은 같은 길이 하나씩 더 있다는 안내
  cv.txt(852, Y - 26, "초록 LED 는 D9,", 12, color=MUTE)
  cv.txt(852, Y - 8, "파랑 LED 는 D10 으로", 12, color=MUTE)
  cv.txt(852, Y + 10, "똑같은 길이 하나씩", 12, color=MUTE)
  cv.txt(852, Y + 28, "더 있다.", 12, color=MUTE)

  cv.note(40, 434, 940, [
    "① USB 케이블을 통해 5V 전기가 보드로 들어온다. 모든 전기의 출발점이다.",
    "② 두뇌 칩이 D8 핀을 5V 로 올린다. 수도꼭지를 여는 것과 같다. 끄면 0V 가 되어 물이 멈춘다.",
    "③ 220Ω 저항이 전기의 양을 줄인다. 이게 없으면 LED 에 전기가 너무 많이 흘러 타 버린다.",
    "④ LED 의 긴 다리로 들어가 짧은 다리로 나오면서 빛이 난다. 반대로 꽂으면 아예 흐르지 않는다.",
    "⑤ GND(− 줄)를 타고 보드로 돌아간다. 여기까지 와야 한 바퀴가 완성된다.",
  ], color=C_R, title="전기가 지나가는 순서")
  return cv


# ======================== 2장 · 검출 LED 2단계 ========================

def sheet2():
  cv = Canvas(1020, 748,
              "빛을 재는 LED — 전기를 채웠다가, 새는 시간을 잰다",
              "이 프로젝트의 핵심. 검출 LED 는 일부러 거꾸로 꽂는다.")

  PW_, PH_ = 462, 300
  AX, BX, PY = 40, 518, 96

  # ---------------- 1단계 · 충전 ----------------
  cv.panel(AX, PY, PW_, PH_)
  cv.txt(AX + 18, PY + 30, "1단계 · 충전", 15.5, weight="700", color=C_DET)
  cv.txt(AX + 130, PY + 30, "전기를 가득 채운다 (0.0001초)", 12.5,
         color=MUTE)

  y = PY + 150
  pin_box(cv, AX + 22, y - 24, 92, 48, "D7", "5V 로 민다", C_DET)
  cv.flow_arrows([(AX + 114, y), (AX + 170, y)], C_DET, 3.4)

  cv.led(AX + 176, y, C_DET, flip=True, size=24)
  cv.txt(AX + 188, y + 42, "검출 LED (거꾸로)", 12.5, anchor="middle",
         weight="700", color=C_DET)

  # 통과 못 한다는 X 표시
  cx, cyy = AX + 188, y
  cv.line(cx - 16, cyy - 16, cx + 16, cyy + 16, RED, 3.4)
  cv.line(cx + 16, cyy - 16, cx - 16, cyy + 16, RED, 3.4)
  cv.txt(AX + 66, y + 74, "전기가 통과하지 못한다", 12.5, weight="700",
         color=RED)
  cv.txt(AX + 66, y + 92, "→ 갈 곳이 없어 LED 안에 고인다", 12, color=MUTE)

  # 고이는 전하 표시
  for i in range(4):
    cv.txt(AX + 122 + i * 12, y - 18, "+", 15, weight="700", color=C_DET)

  cv.line(AX + 197, y, AX + 252, y, MUTE, 2.0, dash="5 4")
  cv.line(AX + 252, y, AX + 252, y + 26, MUTE, 2.0, dash="5 4")
  gnd_symbol(cv, AX + 252, y + 26)

  cup(cv, AX + 350, y - 62, 62, 132, 0.92, "#c4b5fd")
  cv.txt(AX + 381, y - 74, "가득 찼다", 12.5, anchor="middle", weight="700",
         color=C_DET)
  cv.txt(AX + 381, y + 92, "물컵에 물을", 11.5, anchor="middle", color=MUTE)
  cv.txt(AX + 381, y + 108, "채운 셈", 11.5, anchor="middle", color=MUTE)

  # ---------------- 2단계 · 방전 ----------------
  cv.panel(BX, PY, PW_, PH_)
  cv.txt(BX + 18, PY + 30, "2단계 · 방전", 15.5, weight="700", color="#b45309")
  cv.txt(BX + 130, PY + 30, "빛이 전기를 빼내간다 — 이 시간을 잰다", 12.5,
         color=MUTE)

  pin_box(cv, BX + 22, y - 24, 92, 48, "D7", "입력 = 문 닫음", MUTE,
          dash="5 4")
  cv.line(BX + 114, y, BX + 170, y, MUTE, 2.0, dash="5 4")

  cv.led(BX + 176, y, C_DET, flip=True, size=24)
  cv.txt(BX + 188, y + 42, "검출 LED (거꾸로)", 12.5, anchor="middle",
         weight="700", color=C_DET)

  # 들어오는 빛
  for k in range(3):
    sx, sy = BX + 116 + k * 18, y - 76
    cv.flow_arrows([(sx, sy), (sx + 40, sy + 50)], C_LIGHT, 2.8)
  cv.txt(BX + 100, y - 90, "빛이 들어오면", 12.5, weight="700",
         color="#b45309")

  # 빠져나가는 전기
  cv.flow_arrows([(BX + 197, y), (BX + 252, y), (BX + 252, y + 26)],
                 C_DET, 3.0)
  gnd_symbol(cv, BX + 252, y + 30)
  cv.txt(BX + 66, y + 74, "고인 전기가 조금씩 빠져나간다", 12.5,
         weight="700", color=C_DET)
  cv.txt(BX + 66, y + 92, "→ 밝을수록 빨리 빠진다", 12, color=MUTE)

  cup(cv, BX + 350, y - 62, 62, 132, 0.45, "#c4b5fd", holes=2, drip=2)
  cv.txt(BX + 381, y - 74, "새는 중", 12.5, anchor="middle", weight="700",
         color="#b45309")
  cv.txt(BX + 381, y + 92, "빛 = 컵에 뚫린", 11.5, anchor="middle",
         color=MUTE)
  cv.txt(BX + 381, y + 108, "구멍 크기", 11.5, anchor="middle", color=MUTE)

  # ---------------- 전압 그래프 ----------------
  GX, GY, GW, GH = 40, 424, 940, 192
  cv.panel(GX, GY, GW, GH)
  cv.txt(GX + 18, GY + 28,
         "그래서 무엇을 재는가 — 1.1V 까지 내려가는 데 걸린 시간",
         14.5, weight="700")

  ox, oy = GX + 96, GY + 148          # 그래프 원점
  gw, gh = 690, 88
  cv.line(ox, oy - gh - 8, ox, oy, MUTE, 1.6)
  cv.line(ox, oy, ox + gw, oy, MUTE, 1.6)
  cv.txt(ox - 12, oy - gh - 4, "5V", 11.5, anchor="end", color=MUTE)
  cv.txt(ox - 12, oy + 4, "0V", 11.5, anchor="end", color=MUTE)
  cv.txt(ox + gw, oy + 34, "시간 →", 11.5, anchor="end", color=MUTE)

  # 1.1V 기준선
  ty = oy - gh * (1.1 / 5.0)
  cv.line(ox, ty, ox + gw, ty, RED, 1.8, dash="7 5")
  cv.txt(ox - 12, ty + 4, "1.1V", 11.5, anchor="end", weight="700", color=RED)

  def curve(tau, color, label):
    """지수 방전 곡선 + 1.1V 를 지나는 지점 표시."""
    pts = []
    for i in range(101):
      t = i / 100.0 * gw
      v = 5.0 * math.exp(-(t / gw) * tau)
      pts.append((ox + t, oy - gh * (v / 5.0)))
    d = "M %.1f %.1f" % pts[0] + "".join(" L %.1f %.1f" % p for p in pts[1:])
    cv.path(d, stroke=color, sw=3.0)
    hit = ox + gw * (math.log(5.0 / 1.1) / tau)
    cv.line(hit, ty, hit, oy, color, 1.6, dash="4 4")
    cv.circle(hit, ty, 5.0, fill=color, stroke=PAPER, sw=2.0)
    cv.txt(hit, oy + 18, label, 11.5, anchor="middle", weight="700",
           color=color)
    return hit

  curve(6.0, C_LIGHT, "밝을 때 = 짧다")
  curve(1.9, "#5b21b6", "어두울 때 = 길다")
  cv.txt(ox + 300, oy - gh + 4, "밝을수록 가파르게 떨어진다", 12,
         weight="700", color="#b45309")

  cv.note(40, 638, 940, [
    "전기가 1.1V 아래로 내려가는 순간을 칩 안의 비교기가 알아채고 스톱워치를 멈춘다.",
    "빛이 밝으면 시간이 짧고 어두우면 길다. 그래서 이 시간 하나로 밝기를 숫자로 바꿀 수 있다.",
    "액체가 빛을 많이 삼킬수록 검출 LED 에 닿는 빛이 줄고, 시간은 길어진다.",
  ], color=C_DET, title="핵심")
  return cv


# ======================= 3장 · 빛과 정보의 흐름 =======================

def sheet3():
  cv = Canvas(1020, 510,
              "빛은 어떻게 흐르고, 어떻게 답이 되나",
              "전기가 빛이 되고, 빛이 다시 숫자가 되고, 숫자가 답이 된다.")

  # 차광 챔버
  cv.rect(40, 108, 446, 268, fill="#f1f5f9", stroke=MUTE, sw=1.8, rx=10,
          dash="8 6")
  cv.txt(58, 134, "차광 챔버 — 바깥 빛을 막는 검은 상자", 12.5, weight="700",
         color=MUTE)
  cv.txt(58, 152, "바깥 빛이 새어 들어오면 측정이 엉망이 된다.", 11.5,
         color=MUTE)

  y = 246

  # 발광 LED 3개
  for i, (c, nm) in enumerate(((C_R, "빨강"), ("#16a34a", "초록"),
                               ("#2563eb", "파랑"))):
    cv.led(76, y - 44 + i * 44, c, flip=False, size=15)
    cv.txt(120, y - 39 + i * 44, nm, 11.5, color=MUTE)
  cv.txt(72, y + 96, "발광 LED 3개", 12.5, weight="700")
  cv.txt(72, y + 114, "한 번에 하나만 켠다", 11.5, color=MUTE)

  cv.flow_arrows([(162, y), (222, y)], C_LIGHT, 4.4)
  cv.txt(192, y - 18, "빛", 12.5, anchor="middle", weight="700",
         color="#b45309")

  # 큐벳 (액체)
  cv.rect(228, y - 64, 76, 128, fill="#dbeafe", stroke="#60a5fa", sw=1.8,
          rx=5)
  cv.txt(266, y + 5, "액체", 14, anchor="middle", weight="700",
         color="#1d4ed8")
  cv.txt(266, y + 96, "큐벳 (작은 통)", 12.5, anchor="middle", weight="700")
  cv.txt(266, y + 114, "빛의 일부를 삼킨다", 11.5, anchor="middle",
         color=MUTE)

  cv.flow_arrows([(310, y), (372, y)], C_LIGHT, 2.0)
  cv.txt(341, y - 18, "남은 빛", 12, anchor="middle", weight="700",
         color="#b45309")

  # 검출 LED
  cv.led(384, y, C_DET, flip=True, size=22)
  cv.txt(395, y + 96, "검출 LED 1개", 12.5, anchor="middle", weight="700")
  cv.txt(395, y + 114, "빛을 시간으로 바꾼다", 11.5, anchor="middle",
         color=MUTE)

  cv.flow_arrows([(420, y), (504, y)], C_DET, 3.2)

  # 광학 지문 (막대 3개)
  cv.rect(510, y - 64, 124, 128, fill=PAPER, stroke=EDGE, sw=1.4, rx=6)
  cv.txt(572, y - 44, "광학 지문", 12.5, anchor="middle", weight="700")
  for i, (c, hh) in enumerate(((C_R, 48), ("#16a34a", 24), ("#2563eb", 36))):
    bx = 532 + i * 30
    cv.rect(bx, y + 36 - hh, 20, hh, fill=c, stroke="none", sw=0, rx=2)
  cv.txt(572, y + 56, "숫자 3개", 11.5, anchor="middle", color=MUTE)

  cv.flow_arrows([(658, y), (694, y)], INK, 3.2)

  # 두뇌 칩
  cv.rect(700, y - 54, 140, 108, fill=PAPER, stroke=INK, sw=1.8, rx=8)
  cv.txt(770, y - 26, "ATmega328P", 13.5, anchor="middle", weight="700")
  cv.txt(770, y - 6, "미리 배워둔", 11.5, anchor="middle", color=MUTE)
  cv.txt(770, y + 12, "지문과 견줘본다", 11.5, anchor="middle", color=MUTE)
  cv.txt(770, y + 38, "가장 닮은 것 = 답", 11.5, anchor="middle",
         weight="700", color=GREEN)

  cv.flow_arrows([(842, y), (890, y)], GREEN, 3.2)

  # 화면
  cv.rect(896, y - 44, 92, 88, fill="#0f172a", stroke=INK, sw=1.8, rx=6)
  cv.txt(942, y - 12, "MILK", 15, anchor="middle", weight="700",
         color="#4ade80")
  cv.txt(942, y + 12, "우유", 11.5, anchor="middle", color="#94a3b8")
  cv.txt(942, y + 72, "OLED 화면", 12.5, anchor="middle", weight="700")

  cv.note(40, 402, 940, [
    "빨강·초록·파랑을 하나씩 켜서 세 번 재면, 액체마다 다른 숫자 3개가 나온다. 이것이 광학 지문이다.",
    "사람 지문처럼 액체마다 무늬가 달라서, 미리 배워둔 지문과 견주면 어떤 액체인지 맞힐 수 있다.",
  ], color=GREEN, title="왜 세 가지 색으로 재는가")
  return cv


if __name__ == "__main__":
  outdir = os.path.normpath(OUT)
  if not os.path.isdir(outdir):
    os.makedirs(outdir)
  save("flow1.svg", sheet1())
  save("flow2.svg", sheet2())
  save("flow3.svg", sheet3())
