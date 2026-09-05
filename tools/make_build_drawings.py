# -*- coding: utf-8 -*-
"""
make_build_drawings.py — 차광 챔버 제작 도면 6장 생성

도형 그리기 도구는 `tools/build_drawings_lib.py` 에 있고, 이 파일은
시트별 내용만 담는다. 치수의 출처는 `docs/차광챔버_제작.md` 4절이다.

  1장  무엇을 만드는가 (준비물 + 조립 그림 + 부품 목록)
  2장  1:1 재단 템플릿 ① 바닥·뚜껑·마개
  3장  1:1 재단 템플릿 ② 벽 4장
  4장  1:1 지그·슬릿
  5장  조립 순서 8단계
  6장  단면도·누광 검사·완성 체크리스트
  7장  무엇을 덮는가 (챔버 안 / 밖 경계)

실행:  python tools/make_build_drawings.py [--axis 20]
출력:  figures/build/sheet1.svg ... sheet7.svg

--axis 는 챔버 바닥에서 광축까지의 높이(mm)다. 큐벳을 실측하기 전에는
잠정값 20 을 쓰고, 실측 후 실제 값으로 다시 실행해 3장만 재인쇄한다.
"""

import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_drawings_lib import (
  Sheet, box3d, iso, leader,
  PW, PH, MARGIN, INK, MUTE, RED, BLUE, GREEN, TINT,
  T, IN_W, IN_D, IN_H, OUT_W, OUT_D, CUV, JIG_OPEN, JIG_BAND,
  LED_D, LED_PITCH, WIRE_D,
)

# 지그 프레임: 안쪽 13x13, 띠 폭 8 -> 바깥 29x29
JIG_OUT = JIG_OPEN + 2 * JIG_BAND
JIG_LONG = JIG_OUT          # 29 (긴 조각 2개)
JIG_SHORT = JIG_OPEN        # 13 (짧은 조각 2개)

SLIT_W, SLIT_H = 3.0, 8.0   # 슬릿 구멍
MASK = 25.0                 # 슬릿 마스크 한 변


# ============================ 1장 ============================

def sheet1(axis):
  sh = Sheet(1, "① 무엇을 만드는가",
             "차광 챔버 — 시료를 넣고 빛을 통과시키는 검은 상자입니다")

  sh.band(MARGIN, 25, PW - 2 * MARGIN, 30,
          "이 상자가 하는 일",
          ["빛이 새지 않는 캄캄한 상자 안에서, 한쪽 벽의 LED 가 시료를 비추고",
           "반대쪽 벽의 LED 가 그 빛을 받습니다. 바깥 빛이 조금이라도 들어오면",
           "측정값이 틀어지므로, 안쪽을 검게 만들고 틈을 모두 막는 것이 핵심입니다."])

  # ---- 아이소메트릭 조립 그림 ----
  org, s = (100.0, 132.0), 0.7
  f = lambda p: iso(p, org, s)

  # 바닥
  box3d(sh, (0, 0, 0), (OUT_W, OUT_D, T), org, s,
        top="#e2e8f0", right="#cbd5e1", front="#f1f5f9")
  # 뒤벽 (배선 구멍 쪽)
  box3d(sh, (T, 0, T), (IN_W, T, IN_H), org, s,
        top="#475569", right="#334155", front="#3f4a5a")
  # 좌벽 — 검출 LED
  box3d(sh, (0, 0, T), (T, OUT_D, IN_H), org, s,
        top="#475569", right="#3f4a5a", front="#334155")

  # 지그 (바닥 위 프레임 4조각)
  jx = T + (IN_W - JIG_OUT) / 2.0
  jy = T + (IN_D - JIG_OUT) / 2.0
  for pos, size in (
      ((jx, jy, T), (JIG_LONG, JIG_BAND, T)),
      ((jx, jy + JIG_BAND + JIG_OPEN, T), (JIG_LONG, JIG_BAND, T)),
      ((jx, jy + JIG_BAND, T), (JIG_BAND, JIG_SHORT, T)),
      ((jx + JIG_BAND + JIG_OPEN, jy + JIG_BAND, T), (JIG_BAND, JIG_SHORT, T))):
    box3d(sh, pos, size, org, s, top="#fbbf24", right="#d97706",
          front="#f59e0b")

  # 큐벳
  cx = T + (IN_W - CUV) / 2.0
  cy = T + (IN_D - CUV) / 2.0
  box3d(sh, (cx, cy, T), (CUV, CUV, 45.0), org, s,
        top="#bfdbfe", right="#93c5fd", front="#dbeafe")

  # 검출 LED (좌벽 안쪽으로 튀어나옴)
  box3d(sh, (T, T + IN_D / 2.0 - 2.5, T + axis - 2.5), (7, 5, 5), org, s,
        top="#fca5a5", right="#ef4444", front="#f87171")

  # 우벽 — 오른쪽으로 벌려서, 발광 LED 3개
  wx = T + IN_W + 30.0
  box3d(sh, (wx, 0, T), (T, OUT_D, IN_H), org, s,
        top="#475569", right="#334155", front="#3f4a5a")
  for k in (-1, 0, 1):
    box3d(sh, (wx - 7, T + IN_D / 2.0 + k * LED_PITCH - 2.5, T + axis - 2.5),
          (7, 5, 5), org, s, top="#a7f3d0", right="#10b981", front="#6ee7b7")

  # 뚜껑 + 마개 — 위로 벌려서
  box3d(sh, (T, T, 90.0), (IN_W, IN_D, T), org, s,
        top="#94a3b8", right="#64748b", front="#7c8899")
  box3d(sh, (0, 0, 95.0), (OUT_W, OUT_D, T), org, s,
        top="#e2e8f0", right="#cbd5e1", front="#f1f5f9")

  # 지시선
  leader(sh, f((0, 21, 45)), (52, 112), "④ 좌벽 — 검출 LED 1개", anchor="end")
  leader(sh, f((cx + 6, cy + 6, 30)), (52, 132), "큐벳 (시료를 담는 통)",
         anchor="end")
  leader(sh, f((jx + 3, jy + 3, 2 * T)), (52, 152), "⑧⑨ 지그", anchor="end")
  leader(sh, f((14, 30, 0)), (52, 170), "① 바닥", anchor="end")
  leader(sh, f((25, 21, 100)), (146, 60), "② 뚜껑 + ③ 마개")
  leader(sh, f((25, 0, 50)), (146, 88), "⑦ 뒤벽 — 배선 구멍")
  leader(sh, f((wx + T, 21, 50)), (146, 116), "⑤ 우벽")
  leader(sh, f((wx - 4, 21 + LED_PITCH, T + axis)), (146, 140),
         "발광 LED 3개")

  sh.txt(PW / 2.0, 176,
         "※ 안이 보이도록 앞벽(⑥)과 우벽(⑤)을 치우고 그린 그림입니다.",
         2.9, anchor="middle", color=MUTE, italic=True)

  # ---- 부품 목록 ----
  ty = 186
  sh.txt(MARGIN, ty, "우드락(5mm 두께)에서 잘라낼 조각 — 10종 12장",
         4.4, weight="700")
  sh.txt(PW - MARGIN, ty, "다 합쳐 약 171cm². A4 크기 우드락 1장이면 넉넉합니다.",
         3.0, anchor="end", color=MUTE)
  ty += 6
  cols = [MARGIN + 2, MARGIN + 16, MARGIN + 74, MARGIN + 122, MARGIN + 160]
  sh.rect(MARGIN, ty, PW - 2 * MARGIN, 7, fill=TINT, stroke="none")
  for x, h in zip(cols, ["번호", "이름", "치수", "개수", "비고"]):
    sh.txt(x, ty + 4.8, h, 3.1, weight="700")
  ty += 7
  rows = [
    ("①", "바닥", "50 × 43 mm", "1", ""),
    ("②", "뚜껑", "50 × 43 mm", "1", ""),
    ("③", "뚜껑 마개", "40 × 33 mm", "1", "뚜껑 안쪽에 붙임"),
    ("④", "좌벽 — 검출 LED", "43 × 65 mm", "1", "구멍 1개"),
    ("⑤", "우벽 — 발광 LED", "43 × 65 mm", "1", "구멍 3개"),
    ("⑥", "앞벽", "40 × 65 mm", "1", ""),
    ("⑦", "뒤벽", "40 × 65 mm", "1", "배선 구멍 1개"),
    ("⑧", "지그 긴 조각", "29 × 8 mm", "2", "큐벳 자리"),
    ("⑨", "지그 짧은 조각", "13 × 8 mm", "2", "큐벳 자리"),
    ("⑩", "슬릿 마스크", "25 × 25 mm", "1", "검정 도화지. 나중에"),
  ]
  for i, r in enumerate(rows):
    yy = ty + i * 6.2
    if i % 2:
      sh.rect(MARGIN, yy, PW - 2 * MARGIN, 6.2, fill="#f8fafc", stroke="none")
    for x, v in zip(cols, r):
      sh.txt(x, yy + 4.3, v, 3.0)
  ty += len(rows) * 6.2 + 4

  sh.warn(MARGIN, ty, PW - 2 * MARGIN,
          "LED 구멍(④⑤)은 큐벳이 도착한 다음에 뚫으세요",
          ["구멍의 높이 = 빛이 지나가는 높이입니다. 큐벳의 맑은 구간을 재봐야 정해집니다.",
           "지금은 잠정으로 바닥에서 %g mm 로 그려두었습니다. 3장의 빨간 점선이 그 자리입니다."
           % axis])
  sh.foot("우드락 5mm 두께 기준")
  return sh


# ============================ 2장 ============================

def sheet2(axis):
  sh = Sheet(2, "② 재단 템플릿 (1) — 바닥 · 뚜껑 · 마개",
             "실제 크기입니다. 오려서 우드락 위에 대고 그대로 자르세요")

  sh.ruler(MARGIN + 3, 32)

  sh.piece(22, 52, OUT_W, OUT_D, 1, "바닥", "50 × 43 mm · 1장")
  sh.piece(122, 52, OUT_W, OUT_D, 2, "뚜껑", "50 × 43 mm · 1장")
  sh.piece(22, 120, IN_W, IN_D, 3, "뚜껑 마개", "40 × 33 mm · 1장",
           note="뚜껑 아래에 붙여 구멍을 막습니다")

  sh.dim_h(22, 22 + OUT_W, 48, "50 mm")
  sh.dim_v(52, 52 + OUT_D, 17.5, "43 mm")
  sh.dim_h(22, 22 + IN_W, 116, "40 mm")
  sh.dim_v(120, 120 + IN_D, 17.5, "33 mm")

  sh.band(115, 118, 73, 42, "③ 마개가 필요한 이유",
          ["뚜껑을 그냥 얹으면 테두리 틈으로",
           "빛이 들어옵니다. 마개가 상자 안으로",
           "쏙 들어가 빛이 꺾이지 않으면",
           "안까지 못 들어옵니다.",
           "",
           "뚜껑 한가운데에 맞춰 붙이세요."], color=GREEN)

  sh.band(MARGIN, 176, PW - 2 * MARGIN, 52, "자르는 방법",
          ["1.  이 종이를 가위로 오립니다. 검은 실선 바로 바깥을 오리면 됩니다.",
           "2.  우드락 위에 올리고 마스킹테이프로 살짝 고정합니다.",
           "3.  네 모서리의 빨간 십자 표시를 연필로 콕콕 찍어 우드락에 옮깁니다.",
           "4.  종이를 떼고, 찍은 점 4개를 자로 이어 선을 긋습니다.",
           "5.  금속 자를 대고 커터로 자릅니다. 한 번에 깊게 긋지 말고",
           "     같은 자리를 3~4번 살살 그어야 단면이 깨끗합니다.",
           "",
           "※ 커터 날은 새것을 쓰세요. 무딘 날은 우드락을 찢습니다.",
           "※ 자를 때는 반드시 아래에 두꺼운 종이나 책받침을 깝니다."])

  sh.warn(MARGIN, 236, PW - 2 * MARGIN, "손을 다치지 않게",
          ["커터는 자를 잡은 손의 반대 방향으로만 밉니다.",
           "자를 잡은 손가락은 자의 위쪽에 두고, 날이 지나가는 선 옆에 두지 않습니다.",
           "어른과 함께 하세요."])
  sh.foot("1:1 실척 · 인쇄 배율 100%")
  return sh


# ============================ 3장 ============================

def sheet3(axis):
  sh = Sheet(3, "③ 재단 템플릿 (2) — 벽 4장",
             "실제 크기입니다. LED 구멍은 큐벳을 잰 뒤에 뚫습니다")

  sh.ruler(MARGIN + 3, 32)

  wy = 65.0 - axis   # 조각 위쪽 기준 구멍 높이
  cxw = OUT_D / 2.0  # 벽 조각의 가로 중심 (43 / 2)

  sh.piece(22, 52, OUT_D, IN_H, 4, "좌벽", "43 × 65 mm · 검출 LED",
           holes=[(cxw, wy, LED_D, True, "5mm")])
  sh.piece(122, 52, OUT_D, IN_H, 5, "우벽", "43 × 65 mm · 발광 LED",
           holes=[(cxw - LED_PITCH, wy, LED_D, True, ""),
                  (cxw, wy, LED_D, True, "5mm 3개"),
                  (cxw + LED_PITCH, wy, LED_D, True, "")])
  sh.piece(22, 145, IN_W, IN_H, 6, "앞벽", "40 × 65 mm")
  sh.piece(122, 145, IN_W, IN_H, 7, "뒤벽", "40 × 65 mm · 배선 구멍",
           holes=[(IN_W / 2.0, IN_H - 8.0, WIRE_D, False, "8mm")])

  sh.dim_h(22, 22 + OUT_D, 48, "43 mm")
  sh.dim_v(52, 52 + IN_H, 17.5, "65 mm")
  sh.dim_h(22, 22 + IN_W, 141, "40 mm")

  # 구멍 높이 치수 (좌벽)
  sh.dim_v(52 + wy, 52 + IN_H, 22 + OUT_D + 8,
           "%g mm (잠정)" % axis, color=RED)
  sh.line(22, 52 + wy, 22 + OUT_D + 8, 52 + wy, RED, 0.2, dash="1.2 1.2")
  sh.txt(22 + OUT_D + 11, 52 + wy + 1, "← 빛이 지나가는 높이", 2.8,
         color=RED, weight="700")

  # 발광 LED 간격
  lbl = "%g" % LED_PITCH
  sh.dim_h(122 + cxw - LED_PITCH, 122 + cxw, 52 + wy + 14, lbl, above=False)
  sh.dim_h(122 + cxw, 122 + cxw + LED_PITCH, 52 + wy + 14, lbl, above=False)

  sh.warn(MARGIN, 214, PW - 2 * MARGIN,
          "빨간 점선 구멍은 아직 뚫지 마세요",
          ["구멍 높이는 큐벳의 맑은 구간 한가운데여야 합니다. 큐벳이 오면 자로 재고,",
           "docs/차광챔버_제작.md 4절의 실측 항목을 채운 뒤 이 3장만 다시 인쇄하세요.",
           "재인쇄 방법:  python tools/make_build_drawings.py --axis (잰 값)",
           "",
           "구멍은 LED 가 빡빡하게 끼워질 크기로 뚫습니다. 헐거우면 흔들려서 값이 틀어집니다."])

  sh.band(MARGIN, 252, PW - 2 * MARGIN, 30, "구멍 뚫는 방법",
          ["5mm 드릴이 없으면, 커터 끝으로 중심에 십자를 낸 뒤 LED 를 돌려가며 밀어 넣으세요.",
           "우드락은 무르기 때문에 이 방법으로도 잘 들어가고, 오히려 더 빡빡하게 물립니다.",
           "",
           "⑤ 우벽의 세 구멍은 사이 살이 2mm 뿐입니다. 하나씩 천천히, 옆 구멍 쪽으로 힘을 주지 "
           "마세요.",
           "살이 찢어지면 세 구멍을 이어 17 × 5mm 가로 슬롯으로 만들고 LED 3개를 나란히 "
           "끼우면 됩니다."],
          color=GREEN, lead=4.0)
  sh.foot("1:1 실척 · 광축 %g mm 기준" % axis)
  return sh


# ============================ 4장 ============================

def tag_piece(sh, x, y, w, h, label, sub=""):
  """번호를 바깥에 붙이는 작은 1:1 조각."""
  sh.rect(x, y, w, h, fill="#ffffff", stroke=INK, sw=0.45)
  for cx, cy in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
    sh.line(cx - 2.4, cy, cx + 2.4, cy, RED, 0.25)
    sh.line(cx, cy - 2.4, cx, cy + 2.4, RED, 0.25)
  sh.txt(x, y - 4.6, label, 3.2, weight="700")
  if sub:
    sh.txt(x, y - 1.4, sub, 2.7, color=MUTE)


def sheet4(axis):
  sh = Sheet(4, "④ 재단 템플릿 (3) — 지그 · 슬릿",
             "실제 크기입니다. 작은 조각이라 더 조심해서 자르세요")

  sh.ruler(MARGIN + 3, 32)

  # ---- 지그 ----
  sh.txt(MARGIN, 50, "⑧⑨ 큐벳 지그 — 큐벳이 늘 같은 자리에 놓이게 하는 틀",
         4.4, weight="700")
  sh.txt(MARGIN, 55, "이게 없으면 큐벳을 넣을 때마다 빛이 지나는 길이 달라져서, "
         "챔버를 만든 의미가 절반 사라집니다.", 2.9, color=MUTE)

  gx, gy = 28.0, 64.0
  b, o = JIG_BAND, JIG_OPEN
  sh.rect(gx, gy, JIG_OUT, JIG_OUT, fill="#fef3c7", stroke="none")
  for (px, py, pw, ph) in ((gx, gy, JIG_OUT, b),
                           (gx, gy + b + o, JIG_OUT, b),
                           (gx, gy + b, b, o),
                           (gx + b + o, gy + b, b, o)):
    sh.rect(px, py, pw, ph, fill="#fde68a", stroke=INK, sw=0.4)
  sh.rect(gx + b, gy + b, o, o, fill="#ffffff", stroke="none")
  sh.rect(gx + b + 0.25, gy + b + 0.25, CUV, CUV, fill="none",
          stroke=BLUE, sw=0.35, dash="1.2 1.2")
  sh.txt(gx + JIG_OUT / 2.0, gy + JIG_OUT / 2.0 + 1, "큐벳", 2.8,
         anchor="middle", color=BLUE, weight="700")
  sh.dim_h(gx, gx + JIG_OUT, gy - 4, "29 mm")
  sh.dim_h(gx + b, gx + b + o, gy + JIG_OUT + 8, "13 mm", above=False)
  sh.dim_v(gy, gy + JIG_OUT, gx - 5, "29 mm")
  sh.txt(gx + JIG_OUT / 2.0, gy + JIG_OUT + 16,
         "↑ 조립하면 이 모양", 2.9, anchor="middle", color=MUTE, italic=True)

  tag_piece(sh, 96, 70, JIG_LONG, JIG_BAND, "⑧ 긴 조각 (1)", "29 × 8 mm")
  tag_piece(sh, 96, 90, JIG_LONG, JIG_BAND, "⑧ 긴 조각 (2)", "29 × 8 mm")
  tag_piece(sh, 150, 70, JIG_SHORT, JIG_BAND, "⑨ 짧은 조각 (1)", "13 × 8 mm")
  tag_piece(sh, 150, 90, JIG_SHORT, JIG_BAND, "⑨ 짧은 조각 (2)", "13 × 8 mm")

  sh.band(96, 108, PW - MARGIN - 96, 32, "붙이는 순서",
          ["1.  긴 조각 2장을 위아래에 놓습니다",
           "2.  그 사이에 짧은 조각 2장을 끼웁니다",
           "3.  안쪽 구멍이 13 × 13 mm 인지 확인하고 바닥에 붙입니다"],
          color=GREEN, lead=4.2)

  # ---- 슬릿 ----
  sh.line(MARGIN, 142, PW - MARGIN, 142, "#cbd5e1", 0.3)
  sh.txt(MARGIN, 152, "⑩ 슬릿 마스크 — 나중에 필요해지면 만듭니다",
         4.4, weight="700")
  sh.txt(MARGIN, 157, "검정 도화지로 만듭니다. 우드락이 아닙니다.",
         2.9, color=MUTE)

  mx, my = 30.0, 166.0
  sh.rect(mx, my, MASK, MASK, fill="#334155", stroke=INK, sw=0.45)
  for cx, cy in ((mx, my), (mx + MASK, my), (mx, my + MASK),
                 (mx + MASK, my + MASK)):
    sh.line(cx - 2.4, cy, cx + 2.4, cy, RED, 0.25)
    sh.line(cx, cy - 2.4, cx, cy + 2.4, RED, 0.25)
  hx = mx + (MASK - SLIT_W) / 2.0
  hy = my + (MASK - SLIT_H) / 2.0
  sh.rect(hx, hy, SLIT_W, SLIT_H, fill="#ffffff", stroke=RED, sw=0.4)
  sh.dim_h(mx, mx + MASK, my - 4, "25 mm")
  sh.dim_h(hx, hx + SLIT_W, my + MASK + 7, "3 mm", above=False)
  sh.dim_v(hy, hy + SLIT_H, mx + MASK + 7, "8 mm")
  sh.txt(mx, my + MASK + 16, "가운데 네모난 구멍만 오려냅니다", 2.9,
         color=MUTE, italic=True)

  sh.band(92, 164, PW - MARGIN - 92, 54, "슬릿은 언제 쓰나",
          ["큐벳 속 시료가 지나는 통로가 좁으면(4mm쯤), 5mm LED 의 빛이",
           "통로보다 넓어서 일부가 시료를 안 지나고 옆으로 새어 갑니다.",
           "그 빛은 시료 정보가 없어서 측정을 방해합니다.",
           "",
           "그래서 발광 LED 앞에 이 마스크를 붙여 빛을 좁혀 줍니다.",
           "",
           "단, 빛이 약해지는 대가가 있으니 처음부터 붙이지 말고",
           "시료끼리 값 차이가 잘 안 날 때만 붙이세요."], color=GREEN,
          lead=4.2)

  sh.warn(MARGIN, 230, PW - 2 * MARGIN, "작은 조각 자를 때",
          ["⑨ 짧은 조각은 13 × 8 mm 로 아주 작습니다. 큰 우드락에서 먼저 8mm 폭의",
           "긴 띠를 하나 자른 다음, 그 띠를 13mm 씩 토막 내면 훨씬 쉽고 정확합니다.",
           "손가락을 날 앞에 두지 말고, 조각이 작을수록 핀셋을 쓰세요."])

  sh.band(MARGIN, 268, PW - 2 * MARGIN, 16, "재료 확인",
          ["⑧⑨ 지그 = 우드락 5mm   ·   ⑩ 슬릿 마스크 = 검정 무광 도화지 "
           "(반짝이는 종이는 빛을 반사해서 안 됩니다)"], lead=4.2)
  sh.foot("1:1 실척 · 인쇄 배율 100%")
  return sh


# ============================ 5장 ============================

def mini(sh, org, s, floor=True, walls=0, jig=False, cuvette=False,
         leds=False, lid=False, black=False):
  """조립 단계용 작은 그림. walls = 세운 벽 개수(0/2/4)."""
  wall_top = "#475569" if black else "#cbd5e1"
  wall_r = "#334155" if black else "#94a3b8"
  wall_f = "#3f4a5a" if black else "#b6c2d0"
  if floor:
    box3d(sh, (0, 0, 0), (OUT_W, OUT_D, T), org, s,
          top="#e2e8f0", right="#cbd5e1", front="#f1f5f9")
  if walls >= 2:
    box3d(sh, (0, 0, T), (T, OUT_D, IN_H), org, s,
          top=wall_top, right=wall_f, front=wall_r)
    box3d(sh, (T, 0, T), (IN_W, T, IN_H), org, s,
          top=wall_top, right=wall_r, front=wall_f)
  if jig:
    jx = T + (IN_W - JIG_OUT) / 2.0
    jy = T + (IN_D - JIG_OUT) / 2.0
    box3d(sh, (jx, jy, T), (JIG_OUT, JIG_OUT, T), org, s,
          top="#fbbf24", right="#d97706", front="#f59e0b")
  if cuvette:
    cx = T + (IN_W - CUV) / 2.0
    cy = T + (IN_D - CUV) / 2.0
    box3d(sh, (cx, cy, T), (CUV, CUV, 45.0), org, s,
          top="#bfdbfe", right="#93c5fd", front="#dbeafe")
  if leds:
    box3d(sh, (T, T + IN_D / 2.0 - 2.5, T + 20 - 2.5), (7, 5, 5), org, s,
          top="#fca5a5", right="#ef4444", front="#f87171")
  if walls >= 4:
    box3d(sh, (T + IN_W, 0, T), (T, OUT_D, IN_H), org, s,
          top=wall_top, right=wall_r, front=wall_f)
  if lid:
    box3d(sh, (0, 0, T + IN_H + 6), (OUT_W, OUT_D, T), org, s,
          top="#e2e8f0", right="#cbd5e1", front="#f1f5f9")


def sheet5(axis):
  sh = Sheet(5, "⑤ 조립 순서",
             "위에서 아래로, 왼쪽에서 오른쪽으로 순서대로 하세요")

  steps = [
    ("바닥에 벽 4장 세우기",
     ["바닥(①) 위에 좌벽(④)·우벽(⑤)을 먼저 세웁니다.",
      "그 사이에 앞벽(⑥)·뒤벽(⑦)을 끼웁니다.",
      "아직 붙이지 말고 모양만 맞춰 보세요."],
     dict(walls=4)),
    ("이음새를 테이프로 막기",
     ["모서리 8군데를 검정 절연테이프로 덮습니다.",
      "우드락은 맞대면 반드시 틈이 생깁니다.",
      "예쁘게보다 빈틈없이가 중요합니다."],
     dict(walls=4)),
    ("안쪽을 새까맣게",
     ["안쪽 5면 + 뚜껑 안쪽에 검정 무광 도화지를",
      "붙이거나 검정 테이프를 겹치지 않게 바릅니다.",
      "흰 벽은 빛을 반사해 측정을 망칩니다."],
     dict(walls=4, black=True)),
    ("뒤벽에 배선 구멍",
     ["뒤벽(⑦) 아래쪽에 8mm 구멍 하나만 뚫습니다.",
      "LED 4개의 다리 선이 여기로 나갑니다.",
      "선을 통과시킨 뒤 남는 틈은 테이프로 막습니다."],
     dict(walls=4, black=True)),
    ("큐벳 재고 LED 구멍 뚫기",
     ["큐벳이 오면 맑은 구간을 자로 잽니다.",
      "그 한가운데 높이에 좌벽 1개·우벽 3개를 뚫습니다.",
      "3장을 다시 인쇄해서 쓰면 편합니다."],
     dict(walls=4, black=True, leds=True)),
    ("지그 붙이기",
     ["⑧⑨ 네 조각을 바닥 한가운데에 붙입니다.",
      "안쪽 구멍 13 × 13 mm 를 꼭 확인하세요.",
      "큐벳을 넣었다 뺐다 해보고 붙입니다."],
     dict(walls=4, black=True, jig=True)),
    ("정렬 확인 — 붙이기 전에!",
     ["LED 를 구멍에 꽂고 건전지로 켜 봅니다.",
      "빛이 큐벳 한가운데를 지나 반대편 LED 정면에",
      "닿는지 봅니다. 세 개 모두 확인하세요."],
     dict(walls=4, black=True, jig=True, cuvette=True, leds=True)),
    ("고정하고 뚜껑 완성",
     ["정렬이 맞으면 그때 글루건으로 고정합니다.",
      "뚜껑(②) 아래에 마개(③)를 가운데 맞춰 붙입니다.",
      "다 만든 뒤에는 챔버를 옮기지 마세요."],
     dict(walls=4, black=True, jig=True, cuvette=True, leds=True, lid=True)),
  ]

  x0, y0 = MARGIN, 26.0
  cw, ch = (PW - 2 * MARGIN) / 2.0, 58.0
  for i, (title, body, kw) in enumerate(steps):
    cx = x0 + (i % 2) * cw
    cy = y0 + (i // 2) * ch
    sh.rect(cx, cy, cw - 4, ch - 4, fill="#ffffff", stroke="#e2e8f0",
            sw=0.35, rx=2)
    sh.step_no(cx + 8, cy + 8, i + 1)
    sh.txt(cx + 14, cy + 9.4, title, 4.0, weight="700")
    sh.lines(cx + 14, cy + 17, body, 2.9, 4.2, color=INK)
    mini(sh, (cx + 70, cy + 44), 0.20, **kw)

  sh.warn(MARGIN, 262, PW - 2 * MARGIN, "7번을 건너뛰면 처음부터 다시 만듭니다",
          ["붙이기 전에 빛이 제대로 지나가는지 꼭 확인하세요. 한 번 붙이면 못 고칩니다."])
  sh.foot("조립 순서")
  return sh


# ============================ 6장 ============================

def sheet6(axis):
  sh = Sheet(6, "⑥ 단면도 · 검사 · 체크리스트",
             "다 만든 뒤 이 장으로 확인하세요")

  s = 1.12
  ox, oy = 26.0, 36.0
  X = lambda mm: ox + mm * s
  Y = lambda mm: oy + (75.0 - mm) * s   # 바닥 0mm 이 아래

  sh.txt(MARGIN, 31, "빛이 지나가는 길 (앞에서 자른 단면)", 4.4, weight="700")

  sh.rect(X(0), Y(T), OUT_W * s, T * s, fill="#e2e8f0", stroke=INK, sw=0.4)
  sh.rect(X(0), Y(T + IN_H), T * s, IN_H * s, fill="#475569", stroke=INK,
          sw=0.4)
  sh.rect(X(T + IN_W), Y(T + IN_H), T * s, IN_H * s, fill="#475569",
          stroke=INK, sw=0.4)
  sh.rect(X(0), Y(T + IN_H + T), OUT_W * s, T * s, fill="#e2e8f0",
          stroke=INK, sw=0.4)
  sh.rect(X(T), Y(T + IN_H), IN_W * s, T * s, fill="#94a3b8", stroke=INK,
          sw=0.4)

  jx = T + (IN_W - JIG_OUT) / 2.0
  sh.rect(X(jx), Y(2 * T), JIG_OUT * s, T * s, fill="#fbbf24", stroke=INK,
          sw=0.35)
  cxm = T + (IN_W - CUV) / 2.0
  sh.rect(X(cxm), Y(T + 45), CUV * s, 45 * s, fill="#dbeafe", stroke=BLUE,
          sw=0.4)
  sh.rect(X(cxm), Y(T + 25), CUV * s, 25 * s, fill="#bfdbfe", stroke="none")
  sh.line(X(cxm), Y(T + 25), X(cxm + CUV), Y(T + 25), BLUE, 0.4)

  ay = Y(T + axis)
  sh.line(X(-6), ay, X(OUT_W + 6), ay, RED, 0.5, dash="3 1.5")
  sh.txt(X(OUT_W + 8), ay + 1, "빛이 가는 길", 3.0, color=RED, weight="700")
  sh.rect(X(0) - 5, ay - 2.5 * s, 5 + T * s, 5 * s, fill="#f87171",
          stroke=INK, sw=0.3)
  sh.rect(X(T + IN_W), ay - 2.5 * s, T * s + 5, 5 * s, fill="#6ee7b7",
          stroke=INK, sw=0.3)
  sh.txt(X(-7), ay - 8, "검출 LED", 2.8, color=INK, weight="700")
  sh.txt(X(OUT_W + 7), ay - 8, "발광 LED ×3", 2.8, anchor="end",
         weight="700")

  sh.dim_h(X(T), X(T + IN_W), Y(T + IN_H) + 14, "40 mm (LED 사이)")
  sh.dim_v(ay, Y(T), X(OUT_W) + 11, "%g mm" % axis, color=RED)
  sh.dim_v(Y(T + 25), Y(T), X(OUT_W) + 22, "액면", color=BLUE)

  sh.band(118, 36, PW - MARGIN - 118, 74, "이 그림이 말하는 것",
          ["· 빛은 한 직선 위를 지납니다.",
           "  발광 → 큐벳 한가운데 → 검출",
           "",
           "· 빨간 점선(광축)은 반드시",
           "  액체 속에 잠겨 있어야 합니다.",
           "",
           "· 액면이 광축보다 10mm 넘게",
           "  위에 오도록 시료를 넣습니다.",
           "",
           "· 40mm 는 처음 값입니다. 빛이",
           "  모자라면 LED 를 안으로 밀어",
           "  30mm 까지 좁힐 수 있습니다."], lead=4.2)

  # ---- 누광 검사 ----
  sh.line(MARGIN, 126, PW - MARGIN, 126, "#cbd5e1", 0.3)
  sh.txt(MARGIN, 136, "빛이 새는지 검사하기", 4.4, weight="700")

  sh.band(MARGIN, 141, (PW - 2 * MARGIN) / 2.0 - 3, 46,
          "1단계 — 눈으로",
          ["불을 끈 방에서 뚜껑을 닫고,",
           "바깥에서 손전등을 여러 각도로 비춥니다.",
           "안쪽에서 새어 드는 빛이 보이면",
           "그 자리를 테이프로 막습니다.",
           "",
           "이음새 → 배선 구멍 → 뚜껑 테두리",
           "순서로 잘 샙니다."], color=GREEN, lead=4.2)

  sh.band(PW / 2.0 + 1, 141, (PW - 2 * MARGIN) / 2.0 - 3, 46,
          "2단계 — 펌웨어로 (더 확실함)",
          ["부품이 오면 02_phase1 을 올리고,",
           "① 방 불 켜고 DARK 10회",
           "② 방 불 끄고 DARK 10회",
           "③ 두 평균을 비교",
           "",
           "차이가 크면 빛이 새는 것입니다.",
           "이 수치는 PPT 에도 씁니다."], color=GREEN, lead=4.2)

  # ---- 체크리스트 ----
  sh.txt(MARGIN, 197, "완성 체크리스트", 4.4, weight="700")
  items = [
    "불 끈 방에서 손전등을 비춰도 안쪽으로 빛이 새지 않는다",
    "큐벳(12.5 mm)이 지그 홈(13 × 13 mm)에 흔들림 없이 들어간다",
    "큐벳을 10번 넣었다 뺐다 해도 늘 같은 자리에 앉는다",
    "뚜껑을 여닫아도 LED 위치가 변하지 않는다",
    "빛이 큐벳의 맑은 구간 한가운데를 지난다",
    "광축이 액면보다 10mm 이상 아래에 있다",
    "큐벳의 광로 10mm 방향을 지그에 표시해 두었다",
    "발광–검출 거리를 실제로 재서 적어 두었다",
    "완성 사진을 찍었다 (PPT 3번 슬라이드·동영상 장면 2에 씁니다)",
  ]
  for i, it in enumerate(items):
    sh.check(MARGIN + 2, 206 + i * 6.4, it, 3.1)

  sh.rect(MARGIN, 264, PW - 2 * MARGIN, 12, fill=TINT, stroke="none", rx=1.5)
  for dx, label in ((4, "발광–검출 거리: ______ mm"),
                    (68, "광축 높이: ______ mm"),
                    (124, "표준 주입량: ______ mL")):
    sh.txt(MARGIN + dx, 271.5, label, 3.4, weight="700")
  sh.foot("완성 후 확인")
  return sh


# ============================ 7장 ============================

def sheet7(axis):
  sh = Sheet(7, "⑦ 무엇을 덮는가", "챔버 안에 들어가는 것과, 밖에 남는 것")

  sh.band(MARGIN, 25, PW - 2 * MARGIN, 22, "한 줄로 말하면",
          ["**발광 LED 3개 → 큐벳 → 검출 LED**, 이 세 점을 잇는 직선만 감싸면 됩니다.",
           "빛을 내거나 받는 것만 안에 넣고, 나머지 전자부품은 전부 밖에 둡니다."])

  # ---- 왼쪽: 위에서 본 챔버 ----
  sh.txt(MARGIN, 54, "위에서 내려다본 챔버", 4.4, weight="700")
  sh.txt(MARGIN, 58.5, "안에 무엇이 들어가는지 보는 개념도입니다. "
         "재단 치수는 2·3·4장을 보세요.", 2.8, color=MUTE)

  X0, Y0, W, H = 26.0, 72.0, 100.0, 80.0      # 챔버 외곽 (그림상)
  WT = 10.0                                    # 벽 (5mm 를 2배로)
  IX, IY = X0 + WT, Y0 + WT
  IW, IH = W - 2 * WT, H - 2 * WT
  CX, CY = X0 + W / 2.0, Y0 + H / 2.0

  sh.rect(X0, Y0, W, H, fill="#475569", stroke=INK, sw=0.5, rx=1)
  sh.rect(IX, IY, IW, IH, fill="#eef2f7", stroke=INK, sw=0.4)

  # 지그 프레임 (바깥 29 / 안쪽 13mm)
  sh.rect(CX - 29, CY - 29, 58, 58, fill="none", stroke="#b45309", sw=0.35,
          dash="2 1.5")
  sh.rect(CX - 13, CY - 13, 26, 26, fill="none", stroke="#b45309", sw=0.35,
          dash="2 1.5")
  sh.txt(CX + 26, CY + 25, "지그 (큐벳 자리)", 2.6, anchor="end",
         color="#b45309")

  # 큐벳
  sh.rect(CX - 12.5, CY - 12.5, 25, 25, fill="#dbeafe", stroke=BLUE, sw=0.45)
  sh.txt(CX, CY - 5, "큐벳", 3.0, anchor="middle", weight="700", color=BLUE)

  # 발광 LED 3개 (벽에 박힌다) · 검출 LED 1개
  for dy, col, name in ((-14, RED, "R"), (0, GREEN, "G"), (14, BLUE, "B")):
    sh.circle(X0 + WT / 2.0, CY + dy, 5, fill=col, stroke=INK, sw=0.35)
    sh.txt(X0 + WT / 2.0, CY + dy + 1.3, name, 3.4, anchor="middle",
           weight="700", color="#ffffff")
  sh.circle(X0 + W - WT / 2.0, CY, 5, fill="#6ee7b7", stroke=INK, sw=0.35)
  sh.txt(X0 + W - WT / 2.0, CY + 1.2, "검출", 2.6, anchor="middle",
         weight="700")

  # 광축
  sh.line(IX, CY, IX + IW, CY, RED, 0.5, dash="3 1.5")
  sh.arrow(IX + IW, CY, -1, 0, RED, 2.0)
  sh.txt(IX + 2, CY - 3.5, "빛이 가는 길", 2.7, color=RED, weight="700")

  # 부품 이름 (챔버 위쪽에 모아서)
  for x, label in ((X0 + WT / 2.0, "발광 LED 3개"), (CX, "큐벳 · 지그"),
                   (X0 + W - WT / 2.0, "검출 LED 1개")):
    sh.txt(x, Y0 - 4, label, 3.0, anchor="middle", weight="700")
    sh.line(x, Y0 - 2.6, x, Y0, MUTE, 0.25)

  # 배선 구멍 — 챔버를 드나드는 유일한 통로
  hx, hy = X0 + W - 16, Y0 + H - WT / 2.0
  sh.circle(hx, hy, 4, fill="#f8fafc", stroke=INK, sw=0.4)
  for x1, y1, x2, y2 in ((hx, hy, hx, 157), (hx, 157, 78, 157),
                         (78, 157, 78, 170)):
    sh.line(x1, y1, x2, y2, MUTE, 0.8)
  sh.arrow(78, 170, 0, -1, MUTE, 1.8)
  sh.txt(hx + 6, 156,
         "배선 구멍 — 리드선만 나가고, 남는 틈은 테이프로 막습니다.", 2.8,
         color=MUTE)

  # ---- 오른쪽: 경계 확대 단면 ----
  RX = 132.0
  sh.txt(RX, 54, "경계는 어디인가", 4.4, weight="700")
  sh.txt(RX, 58.5, "벽을 자른 단면 (확대)", 2.8, color=MUTE)

  wx, wy, wh = 154.0, 74.0, 44.0               # 벽 단면
  sh.rect(wx, wy, 12, wh, fill="#475569", stroke=INK, sw=0.4)
  sh.txt(RX + 2, 70, "← 챔버 안", 2.8, weight="700", color=GREEN)
  sh.txt(PW - MARGIN, 70, "챔버 밖 →", 2.8, anchor="end", weight="700",
         color=MUTE)

  led_y = wy + wh / 2.0
  sh.circle(wx + 6, led_y, 6, fill="#fca5a5", stroke=INK, sw=0.4)
  for dy, dx in ((-2.5, 14.0), (2.5, 10.0)):
    sh.line(wx, led_y + dy, wx - dx, led_y + dy, INK, 0.4)
    sh.line(wx - dx, led_y + dy, wx - dx, wy + wh + 4, INK, 0.4)
    sh.arrow(wx - dx, wy + wh + 4, 0, 1, INK, 1.6)
  sh.txt(RX, led_y - 6, "리드선", 2.6, weight="700")
  sh.txt(wx + 6, wy - 2.5, "LED", 2.8, anchor="middle", weight="700")

  sh.lines(RX, 128,
           ["· LED 머리가 5mm 구멍을 **꽉 막아야** 합니다.",
            "  헐거우면 빛도 새고 정렬도 깨집니다.",
            "· 리드선은 챔버 **안쪽**으로 나와, 바닥을",
            "  따라 배선 구멍 하나로만 빠져나갑니다.",
            "· 그 구멍 말고 뚫린 곳이 있으면 안 됩니다."], 2.9, 4.2)

  # ---- 챔버 밖 ----
  sh.rect(MARGIN, 160, PW - 2 * MARGIN, 26, fill="#f8fafc", stroke=MUTE,
          sw=0.4, rx=2, dash="2 1.5")
  sh.txt(MARGIN + 4, 166.5, "여기부터 챔버 밖 — 빛과 상관없는 것들", 3.4,
         weight="700", color=MUTE)
  for bx, bw, label in ((20, 32, "저항 4개"), (56, 44, "MCU 보드"),
                        (104, 32, "OLED 화면"), (140, 24, "버튼"),
                        (168, 24, "USB 전원")):
    sh.rect(bx, 170, bw, 12, fill="#e2e8f0", stroke=MUTE, sw=0.3, rx=1.5)
    sh.txt(bx + bw / 2.0, 177.5, label, 3.0, anchor="middle", weight="700")

  # ---- 안 / 밖 정리 ----
  half = (PW - 2 * MARGIN) / 2.0 - 3
  sh.band(MARGIN, 192, half, 58, "챔버 안 — 반드시 덮습니다",
          ["· **검출 LED 1개** (PD7)",
           "   여기로 드는 빛이 곧 측정값입니다",
           "· **발광 LED 3개** (PB0 · PB1 · PB2)",
           "   밖에 두면 큐벳을 안 거친 빛이 샙니다",
           "· **큐벳 (시료)**",
           "· **지그 ㄷ자 홈** — 큐벳 자리 고정",
           "· (필요하면) **슬릿** — 발광 LED 앞",
           "",
           "이것들을 잇는 직선을 6면으로 감쌉니다.",
           "**뚜껑 안쪽까지** 검게 처리하세요. 위에서",
           "반사돼 내려오는 빛이 의외로 큽니다."],
          color=GREEN, size=3.0, lead=4.0)

  sh.band(PW / 2.0 + 1, 192, half, 58, "챔버 밖 — 덮지 않습니다",
          ["· **MCU 보드** (ATmega328P)",
           "· **OLED 화면**, **버튼**",
           "· **전류 제한 저항 4개**, 브레드보드",
           "· **USB 케이블**, 전원",
           "",
           "빛을 내지도 받지도 않는 것들입니다.",
           "안에 넣으면 자리만 좁아집니다.",
           "",
           "**보드의 전원 표시 LED 를 조심하세요.**",
           "그것 하나가 챔버 안에 있으면 계속 켜진",
           "빛이 되어 측정이 통째로 망가집니다."],
          color=MUTE, size=3.0, lead=4.0)

  sh.band(MARGIN, 254, PW - 2 * MARGIN, 22,
          "덮을 곳을 다 덮었는지 확인하는 법",
          ["① 뚜껑을 닫고 **방 불을 켠 채로** DARK 10회  →  "
           "② 방 불만 끄고 DARK 10회  →  ③ 두 평균을 비교",
           "거의 같으면 성공입니다. 불 켠 쪽이 뚜렷하게 짧으면 새는 것이니 "
           "이음새 → 배선 구멍 → 뚜껑 테두리 순으로 막으세요."],
          color=GREEN, size=2.9, lead=4.4)

  sh.foot("챔버가 덮는 범위")
  return sh


# ============================ 실행 ============================

def main():
  ap = argparse.ArgumentParser(description="차광 챔버 제작 도면 생성")
  ap.add_argument("--axis", type=float, default=20.0,
                  help="챔버 바닥에서 광축까지 높이(mm). 기본 20 (잠정값)")
  args = ap.parse_args()

  if not 5.0 <= args.axis <= IN_H - 5.0:
    ap.error("--axis 는 5 ~ %g mm 사이여야 합니다" % (IN_H - 5.0))

  check_geometry()

  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  outdir = os.path.join(root, "figures", "build")
  if not os.path.isdir(outdir):
    os.makedirs(outdir)

  for i, fn in enumerate((sheet1, sheet2, sheet3, sheet4, sheet5,
                          sheet6, sheet7), 1):
    svg = fn(args.axis).render()
    check(svg, i)
    path = os.path.join(outdir, "sheet%d.svg" % i)
    with io.open(path, "w", encoding="utf-8") as f:
      f.write(svg)
    print("생성: figures/build/sheet%d.svg" % i)

  print("광축 높이 %g mm 기준. 큐벳 실측 후 --axis 로 다시 실행하세요."
        % args.axis)


def check(svg, i):
  """1:1 이 깨지지 않았는지 자체 점검."""
  if 'width="210mm" height="297mm"' not in svg:
    raise SystemExit("%d장: 용지 크기가 A4(210x297mm)가 아닙니다" % i)
  if 'viewBox="0 0 210 297"' not in svg:
    raise SystemExit("%d장: viewBox 가 1단위=1mm 가 아닙니다" % i)


def check_geometry():
  """치수끼리 모순이 없는지 점검한다. 상수를 손대면 여기서 걸린다."""
  bad = []
  if IN_W + 2 * T != OUT_W or IN_D + 2 * T != OUT_D:
    bad.append("외곽 치수가 내부 + 벽 두께와 맞지 않는다")
  if JIG_OUT > IN_W or JIG_OUT > IN_D:
    bad.append("지그(%gmm)가 챔버 바닥(%g x %g)보다 크다"
               % (JIG_OUT, IN_W, IN_D))
  if JIG_OPEN <= CUV:
    bad.append("지그 홈(%gmm)이 큐벳(%gmm)보다 작다" % (JIG_OPEN, CUV))
  if 2 * JIG_BAND + JIG_OPEN != JIG_OUT:
    bad.append("지그 조각을 모아도 프레임이 되지 않는다")
  if 2 * LED_PITCH + LED_D >= OUT_D:
    bad.append("발광 LED 3개가 벽 폭을 넘는다")
  if LED_PITCH - LED_D < 2.0:
    bad.append("LED 구멍 사이 살이 %.1fmm 로 너무 얇다 (2mm 이상 필요). "
               "우드락이 찢어진다" % (LED_PITCH - LED_D))
  if IN_H <= 45:
    bad.append("큐벳(45mm)이 챔버 내부 높이(%gmm)에 들어가지 않는다" % IN_H)
  if bad:
    raise SystemExit("치수 모순 — " + " / ".join(bad))


if __name__ == "__main__":
  main()
