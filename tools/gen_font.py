"""ASCII 0x20~0x5F 64자의 6x8 폰트 테이블을 생성한다.

각 글자는 5픽셀 폭 + 1픽셀 간격 = 6바이트. 바이트 하나가 세로 8픽셀이고
최하위 비트가 맨 위 줄이다 (SSD1306 페이지 주소 모드 규약).
"""
import io

# 5x7 글리프. 행 7개, 각 행 5글자. '#'이 켜진 픽셀.
# 여기에 없는 문자(예: $ % & @ [ ] 등)는 공백으로 채워진다. 화면 문구에
# 쓰이지 않기 때문이며, VERIFY 목록이 이를 강제한다.
GLYPHS = {
    ' ': ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
    '!': ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    '.': ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    '/': ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    ':': ["     ", "  #  ", "  #  ", "     ", "  #  ", "  #  ", "     "],
    '-': ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
    '0': [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    '1': ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    '2': [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    '3': ["#####", "   # ", "  ## ", "    #", "    #", "#   #", " ### "],
    '4': ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    '5': ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    '6': ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    '7': ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    '8': [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    '9': [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    'A': [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'B': ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    'C': [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    'D': ["###  ", "#  # ", "#   #", "#   #", "#   #", "#  # ", "###  "],
    'E': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    'F': ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    'G': [" ### ", "#   #", "#    ", "#  ##", "#   #", "#   #", " ####"],
    'H': ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    'I': [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    'J': ["    #", "    #", "    #", "    #", "#   #", "#   #", " ### "],
    'K': ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    'L': ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    'M': ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    'N': ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    'O': [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'P': ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    'Q': [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    'R': ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    'S': [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    'T': ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    'U': ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    'V': ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    'W': ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    'X': ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    'Y': ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    'Z': ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
}

# 스펙 6절 화면 문구에 실제로 등장하는 모든 문자. 하나라도 글리프가
# 없으면 생성을 중단한다. 빈 글자가 화면에 나가는 사고를 막는다.
VERIFY = (
    "LED PEDD ANALYZER READY SHORT MEASURE LONG LEARN NOT TRAINED "
    "HOLD BTN 2S TO RESULT US DARK DIST THR 1/3 2/3 3/3 "
    "PUT DISTILLED WATER DYE MILK CANCEL SAVED EEPROM CLASSES STORED "
    "ERROR TIMEOUT CHECK POLARITY BACK UNKNOWN LOW SIGNAL OK XX "
    "0123456789.:-!"
)

ORDER = [chr(c) for c in range(0x20, 0x60)]


def glyph_bytes(rows):
    out = []
    for x in range(5):
        b = 0
        for y in range(7):
            if rows[y][x] == '#':
                b |= (1 << y)
        out.append(b)
    out.append(0)  # 글자 사이 간격
    return out


def verify():
    missing = sorted({c for c in VERIFY if c != ' ' and c not in GLYPHS})
    if missing:
        raise SystemExit('글리프 없음: %s' % ' '.join(missing))
    for ch, rows in GLYPHS.items():
        if len(rows) != 7 or any(len(r) != 5 for r in rows):
            raise SystemExit('글리프 크기 오류: %r' % ch)


def main():
    verify()
    lines = []
    lines.append('/*')
    lines.append(' * font6x8.h - 6x8 폰트 테이블 (tools/gen_font.py 로 생성. 직접 수정하지 말 것)')
    lines.append(' *')
    lines.append(' * ASCII 0x20~0x5F 64자. 소문자는 없다 - 화면 문구는 전부 대문자다.')
    lines.append(' * PROGMEM 에 두어 SRAM 을 쓰지 않는다 (384바이트).')
    lines.append(' */')
    lines.append('')
    lines.append('#ifndef FONT6X8_H')
    lines.append('#define FONT6X8_H')
    lines.append('')
    lines.append('#include <stdint.h>')
    lines.append('#include <avr/pgmspace.h>')
    lines.append('')
    lines.append('#define FONT_FIRST_CHAR 0x20')
    lines.append('#define FONT_LAST_CHAR  0x5F')
    lines.append('#define FONT_WIDTH      6')
    lines.append('')
    lines.append('static const uint8_t FONT6X8[64][6] PROGMEM = {')
    for ch in ORDER:
        rows = GLYPHS.get(ch, GLYPHS[' '])
        bs = glyph_bytes(rows)
        name = 'space' if ch == ' ' else ch
        lines.append('  {%s},  /* %s */' % (
            ', '.join('0x%02X' % b for b in bs), name))
    lines.append('};')
    lines.append('')
    lines.append('#endif /* FONT6X8_H */')
    io.open('firmware/common/font6x8.h', 'w', encoding='utf-8',
            newline='\n').write('\n'.join(lines) + '\n')
    print('font6x8.h 생성: %d자' % len(ORDER))


if __name__ == '__main__':
    main()
