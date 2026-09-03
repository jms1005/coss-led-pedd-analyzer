# -*- coding: utf-8 -*-
"""
make_schematic.py — 회로도 SVG 생성기

제출물 「나. 회로도 (PDF 파일)」용 도면을 만든다.
좌표를 손으로 쓰면 실수가 잦으므로 부품 기호를 함수로 정의해 조립한다.

실행:  python tools/make_schematic.py
출력:  figures/fig3_schematic.svg
"""

import io
import os

W, H = 1480, 1200
FONT = "'Malgun Gothic','맑은 고딕','Noto Sans KR',sans-serif"
INK = "#1e293b"

out = []


def add(s):
    out.append(s)


def wire(*pts, **kw):
    """직선 배선. pts는 (x, y) 튜플 나열."""
    color = kw.get("color", INK)
    w = kw.get("w", 2)
    d = " ".join("%g,%g" % p for p in pts)
    add('<polyline points="%s" fill="none" stroke="%s" stroke-width="%g" '
        'stroke-linecap="round" stroke-linejoin="round"/>' % (d, color, w))


def line(x1, y1, x2, y2, w=2.4, color=INK):
    add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'
        % (x1, y1, x2, y2, color, w))


def dot(x, y):
    """접속점(정션). 단순 교차와 구분하기 위해 반드시 찍는다."""
    add('<circle cx="%g" cy="%g" r="4.5" fill="%s"/>' % (x, y, INK))


def txt(x, y, s, size=13, anchor="start", weight="400", color=INK):
    add('<text x="%g" y="%g" font-size="%g" text-anchor="%s" font-weight="%s" '
        'fill="%s">%s</text>' % (x, y, size, anchor, weight, color, s))


def box(x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=0):
    add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s" '
        'stroke="%s" stroke-width="%g"/>' % (x, y, w, h, rx, fill, stroke, sw))


# ---------------------------- 부품 기호 ----------------------------

def resistor_h(xc, y, ref, val):
    """가로 저항 (IEC 60617 직사각형 기호). 반환: 좌우 단자 x."""
    bw, bh = 74, 26
    box(xc - bw / 2.0, y - bh / 2.0, bw, bh)
    txt(xc, y - bh / 2.0 - 10, ref, 13, "middle", "700")
    txt(xc, y + bh / 2.0 + 19, val, 12.5, "middle")
    return xc - bw / 2.0, xc + bw / 2.0


def resistor_v(x, yc, ref, val):
    """세로 저항. 반환: 상하 단자 y."""
    bw, bh = 26, 60
    box(x - bw / 2.0, yc - bh / 2.0, bw, bh)
    txt(x + bw / 2.0 + 9, yc - 2, ref, 13, "start", "700")
    txt(x + bw / 2.0 + 9, yc + 15, val, 12.5, "start")
    return yc - bh / 2.0, yc + bh / 2.0


def cap_v(x, yc, ref, val, side="right"):
    """세로 커패시터. 극판 2장. 반환: 상하 단자 y."""
    pw, gap = 34, 11
    line(x - pw / 2.0, yc - gap / 2.0, x + pw / 2.0, yc - gap / 2.0, 2.6)
    line(x - pw / 2.0, yc + gap / 2.0, x + pw / 2.0, yc + gap / 2.0, 2.6)
    tx = x + pw / 2.0 + 8 if side == "right" else x - pw / 2.0 - 8
    an = "start" if side == "right" else "end"
    txt(tx, yc - 2, ref, 13, an, "700")
    txt(tx, yc + 15, val, 12.5, an)
    return yc - gap / 2.0, yc + gap / 2.0


def crystal_v(x, yc, ref, val):
    """세로 수정 진동자. 극판 2장 + 가운데 직사각형. 반환: 상하 단자 y."""
    pw = 34
    line(x - pw / 2.0, yc - 12, x + pw / 2.0, yc - 12, 2.6)
    line(x - pw / 2.0, yc + 12, x + pw / 2.0, yc + 12, 2.6)
    box(x - 13, yc - 8, 26, 16)
    txt(x - pw / 2.0 - 8, yc - 2, ref, 13, "end", "700")
    txt(x - pw / 2.0 - 8, yc + 15, val, 12.5, "end")
    return yc - 12, yc + 12


def led_h(xa, y, ref, val, detector=False, color=INK):
    """가로 LED. 반환: 좌우 단자 x.

    detector=False : 애노드 왼쪽 / 캐소드 오른쪽, 삼각형이 오른쪽을 향한다.
                     화살표는 바깥쪽 = 발광.
    detector=True  : 캐소드 왼쪽 / 애노드 오른쪽, 삼각형이 왼쪽을 향한다.
                     화살표는 안쪽 = 수광.
    이 방향 차이가 본 회로의 핵심이므로 기호로 명확히 구분한다.
    """
    L, hh = 46, 17
    xb = xa + L
    if not detector:
        add('<path d="M %g %g L %g %g L %g %g Z" fill="none" stroke="%s" '
            'stroke-width="2.2"/>' % (xa, y - hh, xa, y + hh, xb, y, color))
        barx = xb
    else:
        add('<path d="M %g %g L %g %g L %g %g Z" fill="none" stroke="%s" '
            'stroke-width="2.2"/>' % (xb, y - hh, xb, y + hh, xa, y, color))
        barx = xa
    line(barx, y - hh, barx, y + hh, 2.8, color)

    cx = xa + L / 2.0
    for k in (0, 1):
        ox = cx - 9 + k * 16
        if not detector:
            x1, y1, x2, y2 = ox, y - hh - 4, ox + 13, y - hh - 18
        else:
            x1, y1, x2, y2 = ox + 13, y - hh - 18, ox, y - hh - 4
        add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" '
            'stroke-width="1.8" marker-end="url(#tip)"/>'
            % (x1, y1, x2, y2, color))

    txt(cx, y + hh + 21, ref, 13, "middle", "700", color)
    txt(cx, y + hh + 38, val, 12.5, "middle", "400", color)
    return xa, xb


def switch_h(xa, y, ref, val):
    """가로 택트 스위치 (a접점). 반환: 좌우 단자 x."""
    L = 56
    xb = xa + L
    add('<circle cx="%g" cy="%g" r="4" fill="none" stroke="%s" '
        'stroke-width="2"/>' % (xa + 4, y, INK))
    add('<circle cx="%g" cy="%g" r="4" fill="none" stroke="%s" '
        'stroke-width="2"/>' % (xb - 4, y, INK))
    wire((xa + 8, y), (xb - 6, y - 18))
    txt(xa + L / 2.0, y + 27, ref, 13, "middle", "700")
    txt(xa + L / 2.0, y + 44, val, 12.5, "middle")
    return xa, xb


def gnd(x, y):
    """접지 기호. 스터브 + 폭이 줄어드는 가로선 3개."""
    wire((x, y), (x, y + 12))
    for i, w2 in enumerate((18, 11, 5)):
        yy = y + 12 + i * 6
        line(x - w2, yy, x + w2, yy, 2.4)


def vcc(x, y):
    """전원 기호."""
    wire((x, y), (x, y - 18))
    line(x - 16, y - 18, x + 16, y - 18, 2.4)
    txt(x, y - 26, "+5V", 13, "middle", "700")


def netflag(x, y, name, direction="right"):
    """네트 라벨. 같은 이름끼리 전기적으로 연결된 것으로 본다."""
    ww, hh = 64, 24
    if direction == "right":
        pts = "%g,%g %g,%g %g,%g %g,%g %g,%g" % (
            x, y, x + 12, y - hh / 2.0, x + ww, y - hh / 2.0,
            x + ww, y + hh / 2.0, x + 12, y + hh / 2.0)
        tx, an = x + 19, "start"
    else:
        pts = "%g,%g %g,%g %g,%g %g,%g %g,%g" % (
            x, y, x - 12, y - hh / 2.0, x - ww, y - hh / 2.0,
            x - ww, y + hh / 2.0, x - 12, y + hh / 2.0)
        tx, an = x - 19, "end"
    add('<polygon points="%s" fill="#fef9c3" stroke="#a16207" '
        'stroke-width="1.6"/>' % pts)
    txt(tx, y + 5, name, 12.5, an, "700", "#713f12")


# ---------------------------- 도면 조립 ----------------------------

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
    'width="%d" height="%d" font-family="%s">' % (W, H, W, H, FONT))
add('<defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" '
    'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    '<path d="M 0 0 L 10 5 L 0 10 z" fill="%s"/></marker></defs>' % INK)
add('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
box(14, 14, W - 28, H - 28, "none", INK, 2)

# ---- MCU 본체 ----
MX0, MX1, MY0, MY1 = 560, 840, 210, 840
box(MX0, MY0, MX1 - MX0, MY1 - MY0, "#f8fafc")
txt((MX0 + MX1) / 2.0, MY0 + 32, "U1", 17, "middle", "700")
txt((MX0 + MX1) / 2.0, MY0 + 55, "ATmega328P-PU", 15, "middle", "700")
txt((MX0 + MX1) / 2.0, MY0 + 75, "28-pin PDIP", 12, "middle", "400", "#64748b")

LEFT_PINS = [("VCC", 7, 250), ("AVCC", 20, 285), ("AREF", 21, 320),
             ("RESET", 1, 380), ("XTAL1", 9, 460), ("XTAL2", 10, 500),
             ("GND", 8, 770), ("GND", 22, 800)]
RIGHT_PINS = [("PB0", 14, 250), ("PB1", 15, 345), ("PB2", 16, 440),
              ("PD7", 13, 535), ("PD2", 4, 620), ("PD0", 2, 685),
              ("PD1", 3, 721), ("PC4", 27, 767), ("PC5", 28, 803)]

for name, pin, y in LEFT_PINS:
    wire((MX0 - 60, y), (MX0, y))
    txt(MX0 + 10, y + 5, name, 13, "start", "600")
    txt(MX0 - 8, y - 7, str(pin), 11.5, "end", "400", "#64748b")
for name, pin, y in RIGHT_PINS:
    wire((MX1, y), (MX1 + 60, y))
    txt(MX1 - 10, y + 5, name, 13, "end", "600")
    txt(MX1 + 8, y - 7, str(pin), 11.5, "start", "400", "#64748b")

txt(MX1 - 10, 535 - 15, "(AIN1)", 11, "end", "600", "#7c3aed")

# ---- 전원부 ----
wire((190, 140), (470, 140))
vcc(330, 140)
for x, ref, val in ((200, "C1", "100nF"), (260, "C2", "100nF"),
                    (320, "C3", "10uF")):
    dot(x, 140)
    wire((x, 140), (x, 300))
    _, cb = cap_v(x, 312, ref, val)
    wire((x, cb), (x, 356))
    gnd(x, 356)

# VCC / AVCC 급전
wire((460, 140), (460, 285))
dot(460, 140)
wire((460, 250), (MX0 - 60, 250))
wire((460, 285), (MX0 - 60, 285))
dot(460, 250)

# RESET 풀업
wire((400, 140), (400, 195))
dot(400, 140)
_, r4b = resistor_v(400, 225, "R4", "10kΩ")
wire((400, r4b), (400, 380), (MX0 - 60, 380))

# AREF 미사용
txt(MX0 - 70, 325, "N.C.", 12.5, "end", "600", "#64748b")
line(MX0 - 68, 313, MX0 - 56, 327, 2, "#64748b")
line(MX0 - 68, 327, MX0 - 56, 313, 2, "#64748b")

# 클럭
wire((490, 460), (MX0 - 60, 460))
wire((490, 500), (MX0 - 60, 500))
yt, yb = crystal_v(490, 480, "Y1", "16MHz")
wire((490, 460), (490, yt))
wire((490, yb), (490, 500))

dot(490, 460)
wire((490, 460), (360, 460), (360, 545))
_, c4b = cap_v(360, 557, "C4", "22pF", "left")
wire((360, c4b), (360, 601))
gnd(360, 601)

dot(490, 500)
wire((490, 500), (425, 500), (425, 545))
_, c5b = cap_v(425, 557, "C5", "22pF", "right")
wire((425, c5b), (425, 601))
gnd(425, 601)

# MCU 접지
wire((MX0 - 60, 770), (520, 770), (520, 856))
wire((MX0 - 60, 800), (520, 800))
dot(520, 800)
gnd(520, 856)

# ---- 발광부 ----
EMITTERS = [(250, "D1", "Red 630nm", "R1", "#dc2626"),
            (345, "D2", "Green 525nm", "R2", "#16a34a"),
            (440, "D3", "Blue 470nm", "R3", "#2563eb")]
for y, dref, dval, rref, col in EMITTERS:
    wire((MX1 + 60, y), (983, y))
    resistor_h(1020, y, rref, "220Ω")
    wire((1057, y), (1090, y))
    _, lb = led_h(1090, y, dref, dval, False, col)
    wire((lb, y), (1230, y))
for y in (345, 440):
    dot(1230, y)
wire((1230, 250), (1230, 462))
gnd(1230, 462)

# ---- 검출부 ----
wire((MX1 + 60, 535), (1090, 535))
_, d4b = led_h(1090, 535, "D4", "Red / 검출용", True, "#7c3aed")
wire((d4b, 535), (1310, 535))
gnd(1310, 535)

# ---- 측정 시작 버튼 ----
wire((MX1 + 60, 620), (1090, 620))
_, swb = switch_h(1090, 620, "SW1", "측정 시작")
wire((swb, 620), (1230, 620))
gnd(1230, 620)

# ---- 네트 라벨 ----
for y, nm in ((685, "RXD"), (721, "TXD"), (767, "SDA"), (803, "SCL")):
    netflag(MX1 + 60, y, nm)

# ---- 커넥터 ----
box(1010, 890, 190, 116, "#f8fafc")
txt(1105, 913, "J1  UART 헤더", 13, "middle", "700")
for i, nm in enumerate(("RXD", "TXD", "GND")):
    y = 938 + i * 24
    txt(1028, y + 5, str(i + 1), 11.5, "start", "400", "#64748b")
    txt(1050, y + 5, nm, 12.5, "start", "600")

box(1230, 890, 190, 140, "#f8fafc")
txt(1325, 913, "J2  I2C OLED", 13, "middle", "700")
for i, nm in enumerate(("+5V", "GND", "SDA", "SCL")):
    y = 938 + i * 24
    txt(1248, y + 5, str(i + 1), 11.5, "start", "400", "#64748b")
    txt(1270, y + 5, nm, 12.5, "start", "600")
# ---- 주석 ----
box(40, 872, 940, 310, "#fffbeb", "#a16207", 1.6, 6)
txt(58, 898, "주석", 14, "start", "700", "#713f12")

NOTES = [
    ("1.", "D4(검출 LED)는 캐소드가 PD7에 연결된다. 일반 LED 결선과 반대 방향이다.", True),
    ("", "PD7을 HIGH로 구동하면 역방향 바이어스가 걸려 접합 정전용량이 충전되고,", False),
    ("", "핀을 입력으로 전환하면 광전류에 의해 방전된다. 극성을 반대로 연결하면", False),
    ("", "순방향이 되어 전하가 축적되지 않으므로 측정이 성립하지 않는다.", False),
    ("2.", "D4는 반드시 적색을 사용한다. LED는 자기 발광 파장 이하의 빛만 흡수하므로,", True),
    ("", "청색·녹색 소자를 쓰면 Red 채널에서 광전류가 흐르지 않아 TIMEOUT이 된다.", False),
    ("3.", "R1~R3는 220Ω 기준값이며, Phase 1에서 광량을 보고 220Ω~1kΩ 범위에서 조정한다.", False),
    ("4.", "SW1은 ATmega328P 내부 풀업을 사용하므로 외부 풀업 저항이 필요 없다.", False),
    ("5.", "AREF(21번)는 ADC를 사용하지 않으므로 미접속(N.C.)이다. 본 설계는 ADC 대신", False),
    ("", "Analog Comparator와 Timer1 Input Capture로 방전 시간을 측정한다.", False),
    ("6.", "J2에 연결하는 OLED 모듈은 SDA/SCL 풀업 저항을 내장하므로 외부 저항이 없다.", False),
    ("7.", "J1·J2의 핀 이름은 U1 측 네트 라벨과 동일한 네트를 가리킨다.", False),
    ("8.", "시제품은 Arduino Uno 보드로 구현하였다. U1·Y1·C1~C5·R4·J1은 보드에 실장되어", False),
    ("", "있으므로, 브레드보드에 실제로 배선하는 부품은 R1~R3, D1~D4, SW1, J2뿐이다.", False),
]
yy = 922
for num, body, warn in NOTES:
    col = "#b91c1c" if warn else "#3f3f46"
    weight = "700" if warn else "400"
    if num:
        txt(58, yy, num, 12.5, "start", "700", col)
    txt(80, yy, body, 12.5, "start", weight, col)
    yy += 19

# Uno 핀 대응표
txt(640, 922, "Arduino Uno 핀 대응 (보드 실크스크린 표기)", 12.5, "start", "700", "#713f12")
MAPPING = [("PB0", "8"), ("PB1", "9"), ("PB2", "10"), ("PD7", "7"),
           ("PD2", "2"), ("PD0", "0 (RX)"), ("PD1", "1 (TX)"),
           ("PC4", "A4"), ("PC5", "A5")]
for i, (a, b) in enumerate(MAPPING):
    yy2 = 944 + i * 19
    txt(640, yy2, a, 12.5, "start", "600", "#3f3f46")
    txt(692, yy2, "→", 12.5, "start", "400", "#a1a1aa")
    txt(716, yy2, b, 12.5, "start", "400", "#3f3f46")

# 부품기호 D1~D4 와 보드 핀 번호를 혼동하지 않도록 경고를 붙인다
for i, w in enumerate(("※ 도면의 D1~D4는 LED 부품기호이고,",
                       "위 숫자는 보드의 디지털 핀 번호다.",
                       "(예: D2는 녹색 LED, 핀 2는 SW1)")):
    txt(640, 1122 + i * 18, w, 12, "start", "700", "#b91c1c")

# ---- 표제란 ----
box(1010, 1042, 410, 128)
line(1010, 1074, 1420, 1074, 1.4)
line(1010, 1110, 1420, 1110, 1.4)
line(1010, 1140, 1420, 1140, 1.4)
line(1230, 1110, 1230, 1170, 1.4)
txt(1022, 1065, "LED 다파장 재이용 광검출 기반 액체 광학 분석기", 12.5, "start", "700")
txt(1022, 1099, "회로도 — 전체 시스템", 14.5, "start", "700")
txt(1022, 1130, "2026 COSS MCU 응용 경진대회", 11.5, "start", "400", "#52525b")
txt(1022, 1160, "설계: (팀명 기입)", 11.5, "start", "400", "#52525b")
txt(1242, 1130, "Rev. 1.0", 11.5, "start", "400", "#52525b")
txt(1242, 1160, "Sheet 1 / 1", 11.5, "start", "400", "#52525b")

add('</svg>')

path = os.path.join("figures", "fig3_schematic.svg")
io.open(path, "w", encoding="utf-8").write("\n".join(out))
print("생성 완료: %s (%d bytes)" % (path, os.path.getsize(path)))
