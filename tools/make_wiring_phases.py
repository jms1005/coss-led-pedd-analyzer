# -*- coding: utf-8 -*-
"""
make_wiring_phases.py — Phase 2 · Phase 4 전용 배선도 (단계별 A4 2장)

Phase 1 도면(make_wiring_phase1.py)과 같은 취지다. 전체 배선도는 최종
시스템 26칸 기준이라, 중간 단계에서 보면 아직 꽂지 않을 것까지 그려져 있어
혼란스럽다. 이 도면은 **그 단계의 펌웨어가 실제로 건드리는 칸만** 담는다.

  Phase 2 (03_phase2)  R·G·B 3채널 + 검출 LED       21칸
  Phase 4 (04_phase4)  Phase 2 + 버튼 + OLED        26칸

  01_blink 는 배선이 없어 도면을 만들지 않는다. 보드 내장 LED(PB5)만 쓴다.

한 단계가 A4 2장인 이유는 확인표 때문이다. Phase 1 은 11칸이라 배치도와
확인표가 한 장에 들어갔지만, 21~26칸을 같은 장에 넣으면 글자가 너무 작아져
손으로 체크하며 쓰기 어렵다.

  1장  브레드보드 배치도 + 앞 단계에서 늘어난 것
  2장  연결 확인표 + 안 될 때 볼 곳

핀 배정 · 열 번호 · 확인표 문구는 전체 배선도에서 **import 해서 쓴다.**
베껴 두면 한쪽만 고쳤을 때 두 도면이 어긋나기 때문이다.

실행:  python tools/make_wiring_phases.py
출력:  figures/wiring/phase2_1.svg · phase2_2.svg
       figures/wiring/phase4_1.svg · phase4_2.svg
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_drawings_lib import (
  Sheet, PW, MARGIN, INK, MUTE, GREEN, TINT, text_width,
)
import make_wiring_drawings as W


# ---- 단계별로 실제 꽂는 줄 (W.CHECKS 의 채널 이름 기준) ----
USE = {
  2: ("GND", "적", "녹", "청", "검출"),
  4: ("GND", "적", "녹", "청", "검출", "버튼", "OLED"),
}
# 앞 단계에서 새로 늘어나는 줄 — 표에 ＋ 로 표시한다
NEW = {
  2: ("녹", "청"),
  4: ("버튼", "OLED"),
}
# 배치도에 그릴 draw_wiring 단계 (1 GND · 2 저항 · 3 발광 · 4 검출 · 5 버튼)
STEPS = {
  2: (1, 2, 3, 4),
  4: (1, 2, 3, 4, 5),
}
PREV = {2: "Phase 1", 4: "Phase 2"}


def checks(phase):
  """(줄, 이번에 새로 늘어난 줄인가) 목록."""
  return [(row, row[0] in NEW[phase])
          for row in W.CHECKS if row[0] in USE[phase]]


def empty_seat(sh, bb, c_from, c_to, rows):
  """다음 단계에서 쓸 자리를 점선 상자로 비워 둔다."""
  p = bb.p
  bx1 = bb.xy(c_from, "A")[0] - p * 0.6
  bx2 = bb.xy(c_to, "A")[0] + p * 0.6
  by1 = bb.xy(1, "A")[1] - p * 0.6
  by2 = bb.xy(1, "E")[1] + p * 0.6
  sh.rect(bx1, by1, bx2 - bx1, by2 - by1, fill="none", stroke="#cbd5e1",
          sw=0.35, rx=p * 0.2, dash="1.6 1.2")

  # 구멍 위에 글자가 겹치면 읽기 어려우므로 흰 바탕을 깔고 쓴다.
  cx, cy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
  size = p * 0.5
  for i, s in enumerate(rows):
    yy = cy + (i - (len(rows) - 1) / 2.0) * size * 1.7
    w = text_width(s, size)
    sh.rect(cx - w / 2.0 - 1.0, yy - size * 0.85, w + 2.0, size * 1.35,
            fill="#ffffff", stroke="none")
    sh.txt(cx, yy, s, size, anchor="middle", color=MUTE)


def check_table(sh, y, rows):
  """연결 확인표. 반환: 표가 끝난 y."""
  cols = [MARGIN + 2, MARGIN + 8, MARGIN + 24, MARGIN + 110, MARGIN + 168]
  sh.rect(MARGIN, y, PW - 2 * MARGIN, 7, fill=TINT, stroke="none")
  for x, h in zip(cols[1:], ["채널", "연결하는 것", "꽂는 곳", "쓴 선 색"]):
    sh.txt(x, y + 4.8, h, 3.0, weight="700")
  y += 7
  for i, ((ch, what, where, col), is_new) in enumerate(rows):
    yy = y + i * 5.6
    if i % 2:
      sh.rect(MARGIN, yy, PW - 2 * MARGIN, 5.6, fill="#f8fafc", stroke="none")
    sh.check(cols[0], yy + 4.0, "", 3.0)
    # 새로 늘어난 줄만 굵게. 선 색은 맨 오른쪽 점이 알려주므로 여기서는
    # 색을 쓰지 않는다 (GND 줄만 검정이 되어 오히려 튄다).
    sh.txt(cols[1], yy + 4.0, ("＋ " + ch) if is_new else ch, 2.9,
           weight="700" if is_new else "400", color=INK if is_new else MUTE)
    warn_row = "⚠" in what
    sh.txt(cols[2], yy + 4.0, what, 3.0, weight="700" if warn_row else "400",
           color=W.C_DET if warn_row else INK)
    sh.txt(cols[3], yy + 4.0, where, 3.0, weight="700")
    sh.circle(cols[4] + 1.6, yy + 2.9, 1.5, fill=col, stroke="none")
    sh.line(cols[4] + 5, yy + 4.4, PW - MARGIN - 2, yy + 4.4, "#cbd5e1", 0.25)
  return y + len(rows) * 5.6


def oled_module(sh, x, y):
  """OLED 는 브레드보드를 거치지 않으므로 따로 그린다."""
  sh.rect(x, y, 36, 21, fill="#1e293b", stroke=INK, sw=0.4, rx=1.5)
  sh.rect(x + 3, y + 6.0, 30, 11, fill="#0f172a", stroke="#334155", sw=0.3)
  sh.txt(x + 18, y + 4.4, "OLED 0.96 인치", 3.0, anchor="middle",
         weight="700", color="#ffffff")
  sh.txt(x + 18, y + 12.8, "SSD1306 · 0x3C", 2.8, anchor="middle",
         color="#94a3b8")
  pins = (("VCC", "5V"), ("GND", "GND"), ("SDA", "A4"), ("SCL", "A5"))
  for k, (nm, dst) in enumerate(pins):
    yy = y + 2.5 + k * 5.4
    sh.line(x + 36, y + 10.5, x + 42, yy, INK, 0.4)
    sh.line(x + 42, yy, x + 50, yy, INK, 0.4)
    sh.circle(x + 50, yy, 0.8, fill=INK, stroke="none")
    sh.txt(x + 53, yy + 1.1, "%s  →  우노 %s" % (nm, dst), 3.0, weight="700")


# ============================ 1장 — 배치도 ============================

BANNER = {
  2: ("여기까지만 꽂습니다",
      ["Phase 2 펌웨어(03_phase2)는 한 사이클에 DARK → R → G → B 네 채널을 측정합니다.",
       "버튼·OLED 는 이 단계의 코드가 건드리지 않아 아직 꽂지 않습니다."]),
  4: ("마지막 단계입니다 — 26칸 전부를 꽂습니다",
      ["Phase 4 펌웨어(04_phase4)는 버튼으로 측정을 시작하고 결과를 OLED 에 띄웁니다.",
       "Phase 2 의 21칸은 그대로 두고 버튼 3칸과 OLED 4선을 더합니다."]),
}

ADDED = {
  2: ("Phase 1 에서 늘어난 것 — 녹 · 청 채널 10칸",
      ["Phase 1 에서 꽂은 11칸(적색 채널 · 검출 LED · GND)은 **그대로 둡니다.**",
       "발광 LED 3개는 자리만 다르고 연결 모양이 똑같습니다 — 핀 → 저항 → 긴 다리(+),",
       "짧은 다리(−) → GND 줄.  **검출 LED 는 색깔마다가 아니라 전체에 하나뿐입니다.**"]),
  4: ("Phase 2 에서 늘어난 것 — 버튼 3칸 + OLED 4선",
      ["버튼은 가운데 홈을 가로질러 꽂고, 다리 4개 중 **대각선으로 마주 보는 두 개**를 씁니다.",
       "한쪽을 우노 D2, 반대쪽을 GND 줄에 넣습니다. **외부 저항은 필요 없습니다** —",
       "MCU 내부 풀업을 켜기 때문입니다 (firmware/common/button.c)."]),
}

AFTER = {
  2: ("다 꽂은 뒤 — 한 사이클에 네 줄이 나오는지 봅니다",
      ["USB 를 꽂고 **38400 bps, 8N1** 로 받으면 seq 가 같은 **DARK · R · G · B 네 줄**이 한 세트입니다.",
       "· 네 줄은 나오는데 값이 **TIMEOUT** 인 채널이 있는지를 보세요.",
       "· 특정 색만 TIMEOUT → 그 색 LED 의 다리 방향과 저항 연결을 다시 확인합니다."]),
  4: ("다 꽂은 뒤 — 처음에는 NOT TRAINED 가 뜨는 게 정상입니다",
      ["OLED 에 **NOT TRAINED** 가 나오면 배선은 된 것입니다. 버튼을 **2초 길게 눌러** 학습부터 합니다.",
       "짧게 누르면 측정 후 판정, 길게 누르면 3종을 순서대로 측정해 EEPROM 에 저장합니다.",
       "학습 도중 다시 길게 누르면 취소되고 기존 학습 데이터는 보존됩니다."]),
}


def sheet1(phase):
  n = len(checks(phase))
  sub = {2: "R · G · B 3채널 + 검출 LED — 전체 26칸 중 %d칸" % n,
         4: "최종 시스템 — 26칸 전부"}[phase]
  sh = Sheet(1, "Phase %d 배선도 ① 배치도" % phase, sub,
             total=2, doc="Phase %d 배선도" % phase)

  sh.band(MARGIN, 25, PW - 2 * MARGIN, 20, *BANNER[phase])

  sh.txt(MARGIN, 50, "브레드보드 배치 — 열 번호는 전체 배선도와 같습니다",
         4.4, weight="700")
  bb = W.Board(39.0, 64.0, 4.4)
  W.draw_board(sh, bb)
  W.draw_wiring(sh, bb, STEPS[phase])
  if phase == 2:
    empty_seat(sh, bb, W.SW_C1 - 1, W.SW_C2, ["Phase 4", "버튼 자리"])

  if phase == 2:
    sh.band(MARGIN, 156, PW - 2 * MARGIN, 26, *ADDED[phase])
    sh.warn(MARGIN, 190, PW - 2 * MARGIN,
            "검출 LED — 이 회로에서 유일하게 거꾸로 꽂는 부품",
            ["캐소드(−) → 우노 D7,  애노드(+) → GND 입니다. 캐소드는 다리 길이보다",
             "**렌즈 안의 큰 컵**으로 판별하세요. 저항은 넣지 않습니다.",
             "색은 반드시 **적색**. 청·녹은 Red 채널이 광전류를 거의 못 만듭니다."])
    sh.band(MARGIN, 222, PW - 2 * MARGIN, 30, *AFTER[phase], color=GREEN)
  else:
    sh.txt(MARGIN, 158,
           "OLED 화면 — 브레드보드를 거치지 않고 우노에 직접 꽂습니다 (암-수 점퍼 4개)",
           4.4, weight="700")
    oled_module(sh, MARGIN + 6, 164)
    sh.band(MARGIN, 194, PW - 2 * MARGIN, 26, *ADDED[phase])
    sh.band(MARGIN, 228, PW - 2 * MARGIN, 30, *AFTER[phase], color=GREEN)

  sh.foot("핀 배정 출처: firmware/common/")
  return sh


# ============================ 2장 — 확인표 ============================

TROUBLE = {
  2: ["· 값이 **0~1 tick 고정**  →  검출 LED 방향. 그대로 180° 돌려 꽂으세요.",
      "· **전 채널 TIMEOUT**  →  검출 LED 미접속·단선, 또는 GND 가 안 이어진 것.",
      "· **R 만 되고 G·B 는 TIMEOUT**  →  녹·청 LED 의 다리 방향과 저항 연결.",
      "· 채널이 뒤바뀐 것 같다  →  D8·D9·D10 을 2·11·20 열에 맞게 꽂았는지.",
      "· 빛을 막았는데 값이 그대로  →  차광이 정말 됐는지 먼저 의심. 손은 샙니다.",
      "· 값이 매번 크게 흔들림  →  챔버 밀폐와 LED·큐벳 고정 상태."],
  4: ["· 버튼을 눌러도 반응 없음  →  **대각선** 두 다리를 썼는지, D2 와 GND 인지.",
      "· OLED 가 안 켜짐  →  SDA·SCL 이 바뀌었는지, VCC 가 5V 인지, 주소가 0x3C 인지.",
      "· OLED 만 안 나오고 UART 는 나옴  →  측정은 계속됩니다. 로그로 진행해도 됩니다.",
      "· 화면에 **NOT TRAINED**  →  고장이 아닙니다. 2초 길게 눌러 학습부터 하세요.",
      "· 값이 **0~1 tick 고정**  →  검출 LED 방향. 그대로 180° 돌려 꽂으세요.",
      "· **전 채널 TIMEOUT**  →  검출 LED 미접속·단선, 또는 GND 가 안 이어진 것.",
      "· 특정 색만 이상  →  그 색 LED 의 다리 방향과 저항 연결."],
}


def sheet2(phase):
  rows = checks(phase)
  sh = Sheet(2, "Phase %d 배선도 ② 연결 확인표" % phase,
             "USB 를 꽂기 전에 %d칸을 전부 확인하세요" % len(rows),
             total=2, doc="Phase %d 배선도" % phase)

  sh.txt(MARGIN, 29,
         "＋ 표시한 칸이 %s 에서 새로 늘어난 배선입니다. 나머지는 그대로 두세요."
         % PREV[phase], 3.0, color=MUTE)

  y = check_table(sh, 33, rows) + 6

  y = sh.warn(MARGIN, y, PW - 2 * MARGIN, "USB 를 꽂기 직전에 이 세 가지",
              ["① 검출 LED 의 캐소드(렌즈 안 큰 컵 쪽)가 D7 인가 — 발광 LED 와 반대입니다.",
               "② 5V 와 GND 가 어디에서도 직접 맞닿아 있지 않은가 (합선).",
               "③ 부품 다리끼리 서로 닿아 있지 않은가. 특히 LED 두 다리."]) + 6

  sh.band(MARGIN, y, PW - 2 * MARGIN, 12.0 + len(TROUBLE[phase]) * 4.2 + 2,
          "잘 안 될 때 어디부터 보나", TROUBLE[phase], color=GREEN, lead=4.2)
  sh.foot("확인표 · Phase %d 배선도 끝" % phase)
  return sh


# ============================ 실행 ============================

def main():
  root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  outdir = os.path.join(root, "figures", "wiring")
  if not os.path.isdir(outdir):
    os.makedirs(outdir)

  for phase in (2, 4):
    for i, fn in enumerate((sheet1, sheet2), 1):
      svg = fn(phase).render()
      if 'width="210mm" height="297mm"' not in svg:
        raise SystemExit("Phase %d %d장: 용지 크기가 A4 가 아닙니다"
                         % (phase, i))
      name = "phase%d_%d.svg" % (phase, i)
      with io.open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
        f.write(svg)
      print("generated: figures/wiring/%s" % name)


if __name__ == "__main__":
  main()
