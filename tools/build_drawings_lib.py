# -*- coding: utf-8 -*-
"""
make_build_drawings.py — 차광 챔버 제작 도면 생성기

`docs/차광챔버_제작.md` 의 치수를 그림으로 옮긴다. 인쇄해서 보면서
만들 수 있도록 A4 6장으로 구성하고, 재단 템플릿은 1:1 실척으로 그린다.

  1장  무엇을 만드는가 (준비물 + 조립 그림)
  2장  1:1 재단 템플릿 ① 바닥·뚜껑·마개
  3장  1:1 재단 템플릿 ② 벽 4장
  4장  1:1 지그·슬릿
  5장  조립 순서 8단계
  6장  단면도·누광 검사·체크리스트

핵심 규칙: **SVG 1 단위 = 1mm**. 인쇄 래퍼가 210x297mm 로 고정하므로
템플릿을 오려 우드락에 대고 그대로 자를 수 있다.

실행:  python tools/make_build_drawings.py [--axis 20]
출력:  figures/build/sheet1.svg ... sheet6.svg
"""

import argparse
import io
import os

# ------------------------------ 상수 ------------------------------

PW, PH = 210.0, 297.0        # A4 (mm)
MARGIN = 14.0

FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"              # 본문
MUTE = "#64748b"             # 보조 설명
RED = "#dc2626"              # 경고·미확정
BLUE = "#2563eb"             # 치수선
GREEN = "#059669"            # 확인 항목
PAPER = "#ffffff"
TINT = "#f1f5f9"             # 안내 박스 배경

T = 5.0                      # 우드락 두께
IN_W, IN_D, IN_H = 40.0, 33.0, 65.0         # 챔버 내부 폭·깊이·높이
OUT_W, OUT_D = IN_W + 2 * T, IN_D + 2 * T   # 50 x 43
CUV = 12.5                   # 큐벳 한 변
JIG_OPEN = 13.0              # 지그 안쪽 (큐벳 + 0.5mm 여유)
JIG_BAND = 8.0               # 지그 띠 폭
LED_D = 5.0                  # LED 지름
LED_PITCH = 7.0              # 발광 LED 3개 중심 간격 (구멍 사이 살 2mm 확보)
WIRE_D = 8.0                 # 배선 구멍 지름


def esc(s):
  return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------ 시트 ------------------------------

class Sheet(object):
  """A4 한 장. 모든 좌표는 mm."""

  def __init__(self, num, title, subtitle=""):
    self.num = num
    self.el = []
    self.head(title, subtitle)

  # --- 기본 도형 ---

  def add(self, s):
    self.el.append(s)

  def rect(self, x, y, w, h, fill="none", stroke=INK, sw=0.3, rx=0, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" '
             'fill="%s" stroke="%s" stroke-width="%.2f"%s/>'
             % (x, y, w, h, rx, fill, stroke, sw, d))

  def line(self, x1, y1, x2, y2, stroke=INK, sw=0.3, dash=None, cap="butt"):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
             'stroke-width="%.2f" stroke-linecap="%s"%s/>'
             % (x1, y1, x2, y2, stroke, sw, cap, d))

  def circle(self, cx, cy, r, fill="none", stroke=INK, sw=0.3, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    self.add('<circle cx="%.2f" cy="%.2f" r="%.2f" fill="%s" stroke="%s" '
             'stroke-width="%.2f"%s/>' % (cx, cy, r, fill, stroke, sw, d))

  def poly(self, pts, fill="none", stroke=INK, sw=0.3, dash=None):
    d = ' stroke-dasharray="%s"' % dash if dash else ''
    s = " ".join("%.2f,%.2f" % p for p in pts)
    self.add('<polygon points="%s" fill="%s" stroke="%s" stroke-width="%.2f" '
             'stroke-linejoin="round"%s/>' % (s, fill, stroke, sw, d))

  def txt(self, x, y, s, size=3.2, anchor="start", weight="400", color=INK,
          italic=False):
    st = ' font-style="italic"' if italic else ''
    self.add('<text x="%.2f" y="%.2f" font-size="%.2f" text-anchor="%s" '
             'font-weight="%s" fill="%s"%s>%s</text>'
             % (x, y, size, anchor, weight, color, st, esc(s)))

  def lines(self, x, y, rows, size=3.2, lead=4.4, anchor="start",
            weight="400", color=INK):
    """여러 줄 텍스트. 반환: 마지막 줄의 y."""
    for i, r in enumerate(rows):
      self.txt(x, y + i * lead, r, size, anchor, weight, color)
    return y + (len(rows) - 1) * lead

  # --- 조합 요소 ---

  def head(self, title, subtitle):
    self.line(MARGIN, 22, PW - MARGIN, 22, INK, 0.6)
    self.txt(MARGIN, 13.5, title, 7.2, weight="700")
    if subtitle:
      self.txt(MARGIN, 19.4, subtitle, 3.2, color=MUTE)
    self.txt(PW - MARGIN, 14, "%d / 6" % self.num, 6.0, anchor="end",
             color=MUTE, weight="700")

  def foot(self, note=""):
    self.line(MARGIN, PH - 12, PW - MARGIN, PH - 12, "#cbd5e1", 0.3)
    self.txt(MARGIN, PH - 8, "차광 챔버 제작 도면  ·  LED PEDD 액체 광학 분석기",
             2.6, color=MUTE)
    if note:
      self.txt(PW - MARGIN, PH - 8, note, 2.6, anchor="end", color=MUTE)

  def band(self, x, y, w, h, title, rows, color=BLUE, size=3.2, lead=4.4):
    """제목이 붙은 안내 박스."""
    self.rect(x, y, w, h, fill=TINT, stroke="none", rx=1.5)
    self.rect(x, y, 1.2, h, fill=color, stroke="none")
    self.txt(x + 4, y + 5.6, title, 3.8, weight="700", color=color)
    self.lines(x + 4, y + 11.4, rows, size, lead)

  def warn(self, x, y, w, title, rows):
    h = 12.0 + len(rows) * 4.4
    self.rect(x, y, w, h, fill="#fef2f2", stroke=RED, sw=0.4, rx=1.5)
    self.txt(x + 4, y + 6.2, title, 3.8, weight="700", color=RED)
    self.lines(x + 4, y + 12.0, rows, 3.2, 4.4)
    return y + h

  def step_no(self, x, y, n, color=INK):
    """동그란 단계 번호."""
    self.circle(x, y, 3.4, fill=color, stroke="none")
    self.txt(x, y + 1.3, str(n), 3.8, anchor="middle", weight="700",
             color="#ffffff")

  def check(self, x, y, label, size=3.2):
    self.rect(x, y - 2.6, 3.4, 3.4, fill="none", stroke=INK, sw=0.35, rx=0.4)
    self.txt(x + 5.4, y, label, size)

  # --- 치수선 ---

  def arrow(self, x, y, dx, dy, color=BLUE, s=1.5):
    if dx:
      pts = [(x, y), (x + dx * s, y - s * 0.45), (x + dx * s, y + s * 0.45)]
    else:
      pts = [(x, y), (x - s * 0.45, y + dy * s), (x + s * 0.45, y + dy * s)]
    self.poly(pts, fill=color, stroke="none")

  def dim_h(self, x1, x2, y, label, color=BLUE, tick=1.6, above=True):
    self.line(x1, y - tick, x1, y + tick, color, 0.25)
    self.line(x2, y - tick, x2, y + tick, color, 0.25)
    self.line(x1, y, x2, y, color, 0.25)
    self.arrow(x1, y, 1, 0, color)
    self.arrow(x2, y, -1, 0, color)
    dy = -1.6 if above else 3.6
    self.txt((x1 + x2) / 2.0, y + dy, label, 3.0, anchor="middle",
             weight="700", color=color)

  def dim_v(self, y1, y2, x, label, color=BLUE, tick=1.6):
    self.line(x - tick, y1, x + tick, y1, color, 0.25)
    self.line(x - tick, y2, x + tick, y2, color, 0.25)
    self.line(x, y1, x, y2, color, 0.25)
    self.arrow(x, y1, 0, 1, color)
    self.arrow(x, y2, 0, -1, color)
    cy = (y1 + y2) / 2.0
    self.add('<text x="%.2f" y="%.2f" font-size="3.0" text-anchor="middle" '
             'font-weight="700" fill="%s" transform="rotate(-90 %.2f %.2f)">'
             '%s</text>' % (x - 1.6, cy, color, x - 1.6, cy, esc(label)))

  def ruler(self, x, y, label=True):
    """인쇄 배율 검증용 100mm 눈금자."""
    self.line(x, y, x + 100, y, INK, 0.4)
    for i in range(11):
      h = 3.2 if i % 5 == 0 else 1.8
      self.line(x + i * 10, y, x + i * 10, y - h, INK, 0.35)
      if i % 5 == 0:
        self.txt(x + i * 10, y - 4.2, "%d" % (i * 10), 2.6, anchor="middle",
                 color=MUTE)
    self.txt(x + 103, y + 1.0, "mm", 2.6, color=MUTE)
    if label:
      self.txt(x, y + 5.4,
               "↑ 인쇄한 뒤 이 줄을 자로 재보세요. 정확히 100mm 가 아니면 "
               "인쇄 설정을 '실제 크기 100%' 로 바꿔 다시 뽑으세요.",
               2.8, color=RED, weight="700")

  # --- 재단 조각 ---

  def piece(self, x, y, w, h, no, name, spec, holes=None, note=None):
    """1:1 재단 조각. holes = [(cx, cy, d, dashed, tag), ...] 조각 기준 좌표."""
    self.rect(x - 2.5, y - 2.5, w + 5, h + 5, fill="none", stroke="#cbd5e1",
              sw=0.2, dash="1.5 1.5", rx=1)
    self.rect(x, y, w, h, fill="#ffffff", stroke=INK, sw=0.45)
    for cx, cy in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
      self.line(cx - 3, cy, cx + 3, cy, RED, 0.25)
      self.line(cx, cy - 3, cx, cy + 3, RED, 0.25)
    self.step_no(x + 6.5, y + 6.5, no)
    self.txt(x + 12, y + 6.0, name, 3.6, weight="700")
    self.txt(x + 12, y + 10.2, spec, 2.8, color=MUTE)
    for (cx, cy, d, dashed, tag) in (holes or []):
      self.circle(x + cx, y + cy, d / 2.0, fill="none",
                  stroke=RED if dashed else INK, sw=0.4,
                  dash="1.2 1.2" if dashed else None)
      self.line(x + cx - 2.4, y + cy, x + cx + 2.4, y + cy, MUTE, 0.2)
      self.line(x + cx, y + cy - 2.4, x + cx, y + cy + 2.4, MUTE, 0.2)
      if tag:
        self.txt(x + cx, y + cy - d / 2.0 - 1.8, tag, 2.5, anchor="middle",
                 color=RED if dashed else MUTE, weight="700")
    if note:
      self.txt(x + w / 2.0, y + h + 6.5, note, 2.8, anchor="middle",
               color=MUTE, italic=True)

  # --- 출력 ---

  def render(self):
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" '
      'viewBox="0 0 %g %g" font-family="%s">\n'
      '<rect width="%g" height="%g" fill="%s"/>\n%s\n</svg>\n'
      % (PW, PH, PW, PH, FONT, PW, PH, PAPER, "\n".join(self.el)))


# --------------------------- 아이소메트릭 ---------------------------

COS30, SIN30 = 0.8660254, 0.5


def iso(p, org, s):
  """(x, y, z) mm -> 화면 좌표. +x 오른쪽아래, +y 왼쪽아래, +z 위."""
  x, y, z = p
  return (org[0] + (x - y) * COS30 * s,
          org[1] + ((x + y) * SIN30 - z) * s)


def box3d(sh, pos, size, org, s, top="#e2e8f0", right="#cbd5e1",
          front="#f8fafc", stroke=INK, sw=0.28, dash=None):
  """직육면체. 보이는 세 면(+y / +x / 위)만 그린다."""
  x, y, z = pos
  dx, dy, dz = size
  f = lambda p: iso(p, org, s)
  faces = [
    (front, [(x, y + dy, z), (x + dx, y + dy, z),
             (x + dx, y + dy, z + dz), (x, y + dy, z + dz)]),
    (right, [(x + dx, y, z), (x + dx, y + dy, z),
             (x + dx, y + dy, z + dz), (x + dx, y, z + dz)]),
    (top, [(x, y, z + dz), (x + dx, y, z + dz),
           (x + dx, y + dy, z + dz), (x, y + dy, z + dz)]),
  ]
  for fill, pts in faces:
    sh.poly([f(p) for p in pts], fill=fill, stroke=stroke, sw=sw, dash=dash)


def leader(sh, p_from, p_to, label, color=INK, anchor="start"):
  """지시선 + 라벨."""
  sh.line(p_from[0], p_from[1], p_to[0], p_to[1], color, 0.25)
  sh.circle(p_from[0], p_from[1], 0.7, fill=color, stroke="none")
  dx = 1.6 if anchor == "start" else -1.6
  sh.txt(p_to[0] + dx, p_to[1] + 1.0, label, 3.0, anchor=anchor,
         weight="700", color=color)
