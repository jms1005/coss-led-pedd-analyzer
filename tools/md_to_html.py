# -*- coding: utf-8 -*-
"""
md_to_html.py — 마크다운 문서를 인쇄용 HTML 로 감싼다.

`tools/make_doc_pdf.sh` 가 부르는 보조 스크립트다. 직접 쓸 일은 없다.

도면 스크립트들과 달리 이쪽은 **원본이 마크다운**이라, 표·인용·코드블록이
A4 에서 읽히도록 스타일을 입히는 것이 일의 대부분이다.

실행:  python tools/md_to_html.py <입력.md> <출력.html> [문서제목]
"""

import io
import os
import re
import sys

import markdown

# Windows 콘솔 기본 코드페이지(cp949)에서 한글·기호가 깨지지 않도록 고정.
# analyze.py 와 같은 처리다. 이게 없으면 제목에 —(em dash)만 들어가도
# UnicodeEncodeError 로 죽는다.
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # Python 3.6 이하

# 인쇄용 스타일. 화면이 아니라 A4 종이가 기준이다.
CSS = u"""
@page { size: A4; margin: 16mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Malgun Gothic', '맑은 고딕', 'Noto Sans KR', sans-serif;
  font-size: 9.6pt; line-height: 1.62; color: #1e293b; margin: 0;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
h1 { font-size: 19pt; margin: 0 0 4mm; padding-bottom: 3mm;
     border-bottom: 2.4pt solid #f15c22; letter-spacing: -0.4pt; }
h2 { font-size: 13.5pt; margin: 8mm 0 3mm; padding-left: 2.6mm;
     border-left: 3.4pt solid #f15c22; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 6mm 0 2mm; color: #334155;
     page-break-after: avoid; }
h4 { font-size: 10pt; margin: 4mm 0 1.5mm; color: #475569;
     page-break-after: avoid; }
p { margin: 0 0 2.4mm; }
ul, ol { margin: 0 0 2.6mm; padding-left: 6.5mm; }
li { margin-bottom: 1.1mm; }
strong { color: #0f172a; }
a { color: #1d4ed8; text-decoration: none; }
code {
  font-family: Consolas, 'D2Coding', monospace; font-size: 8.7pt;
  background: #f1f5f9; padding: 0.4mm 1.1mm; border-radius: 1mm;
  color: #b91c1c;
}
pre {
  background: #f8fafc; border: 0.3mm solid #cbd5e1; border-radius: 1.2mm;
  padding: 2.6mm 3mm; overflow: hidden; margin: 0 0 3mm;
  page-break-inside: avoid;
}
pre code {
  background: none; padding: 0; color: #1e293b; font-size: 8.3pt;
  line-height: 1.45; white-space: pre-wrap; word-break: break-all;
}
blockquote {
  margin: 0 0 3mm; padding: 2.2mm 3mm; background: #fffbeb;
  border-left: 2.6pt solid #a16207; color: #713f12;
  page-break-inside: avoid;
}
blockquote p { margin: 0 0 1.6mm; }
blockquote p:last-child { margin-bottom: 0; }
table {
  border-collapse: collapse; width: 100%; margin: 0 0 3.4mm;
  font-size: 8.9pt; page-break-inside: avoid;
}
th {
  background: #334155; color: #fff; font-weight: 700; text-align: left;
  padding: 1.5mm 2mm; border: 0.25mm solid #334155;
}
td { padding: 1.4mm 2mm; border: 0.25mm solid #cbd5e1; vertical-align: top; }
tr:nth-child(even) td { background: #f8fafc; }
hr { border: none; border-top: 0.3mm solid #e2e8f0; margin: 5mm 0; }
/* 문단이 페이지 경계에서 한 줄만 남는 것을 막는다 */
p, li { orphans: 2; widows: 2; }
.doc-foot {
  margin-top: 7mm; padding-top: 2.5mm; border-top: 0.3mm solid #e2e8f0;
  font-size: 8pt; color: #64748b;
}
"""

TEMPLATE = u"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>%(title)s</title><style>%(css)s</style></head>
<body>
%(body)s
<div class="doc-foot">%(foot)s</div>
</body></html>
"""


def convert(src, dst, title=None):
    text = io.open(src, encoding='utf-8').read()

    # 저장소 안 상대 링크(.md)는 PDF 에서 열리지 않는다. 텍스트만 남긴다.
    text = re.sub(r'\[([^\]]+)\]\((?!https?:)[^)]+\)', r'\1', text)

    # nl2br 은 쓰지 않는다. 원본 마크다운이 72자쯤에서 손으로 줄바꿈되어
    # 있어서, 그것을 <br> 로 바꾸면 A4 폭의 절반에서 문단이 끊겨 읽기
    # 나빠진다. 종이에서는 문단이 페이지 폭에 맞춰 흘러야 한다.
    html = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'sane_lists'],
    )

    if title is None:
        m = re.search(r'^#\s+(.+)$', text, re.M)
        title = m.group(1).strip() if m else os.path.basename(src)

    foot = (u'출처: %s — 2026 COSS 차세대반도체 MCU 응용 경진대회. '
            u'이 PDF 는 tools/make_doc_pdf.sh 가 생성합니다. '
            u'내용을 고치려면 원본 마크다운을 고치고 다시 만드세요.'
            % os.path.basename(src))

    io.open(dst, 'w', encoding='utf-8').write(
        TEMPLATE % {'title': title, 'css': CSS, 'body': html, 'foot': foot})
    return title


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    t = convert(sys.argv[1], sys.argv[2],
                sys.argv[3] if len(sys.argv) > 3 else None)
    print(u'HTML 생성: %s (제목: %s)' % (sys.argv[2], t))
