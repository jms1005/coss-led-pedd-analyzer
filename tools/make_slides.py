# -*- coding: utf-8 -*-
"""
make_slides.py — 슬라이드 데이터 + 테마 -> HTML, 렌더된 PNG -> 시안 pptx

내용은 slide_content.py, 디자인은 slides.css 에 있다. 이 파일은 둘을
조립하기만 한다. 도면을 SVG 로 뽑는 make_build_drawings.py 와 같은 구조다.

실행:
  python tools/make_slides.py          HTML 생성 (figures/slides/)
  python tools/make_slides.py --pptx   렌더된 PNG 를 시안 pptx 로 묶음

보통은 직접 부르지 않고 sh tools/make_slides.sh 를 쓴다.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slide_content

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures", "slides")
PNG = os.path.join(ROOT, "제출물", "디자인시안")

THEMES = [("dark", "계기판"), ("paper", "논문")]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------- 슬라이드 유형별 본문 ----------------------------

def body_cover(d):
    title = "<br>".join(esc(t) for t in d["title"])
    meta = "\n".join(
        '      <div><b>%s</b>%s</div>' % (esc(k), esc(v)) for k, v in d["meta"])
    return (
        '  <div class="cover">\n'
        '    <div class="kicker">%s</div>\n'
        '    <h1>%s</h1>\n'
        '    <div class="rule"></div>\n'
        '    <div class="lede">%s</div>\n'
        '    <div class="meta">\n%s\n    </div>\n'
        '  </div>' % (esc(d["kicker"]), title, esc(d["lede"]), meta))


def body_bullets(d):
    li = []
    for text, lvl, hi in d["items"]:
        cls = "lv%d%s" % (lvl, " hi" if hi else "")
        li.append('      <li class="%s">%s</li>' % (cls, esc(text)))
    return '  <main>\n    <ul class="bul">\n%s\n    </ul>\n  </main>' % "\n".join(li)


def body_table(d):
    th = "".join("<th>%s</th>" % esc(h) for h in d["headers"])
    trs = []
    for row in d["rows"]:
        tds = []
        for val in row:
            hi = val.startswith("*")
            tds.append('<td%s>%s</td>' % (' class="hi"' if hi else "",
                                          esc(val.lstrip("*"))))
        trs.append("      <tr>%s</tr>" % "".join(tds))
    return ('  <main>\n    <table>\n      <thead><tr>%s</tr></thead>\n'
            '      <tbody>\n%s\n      </tbody>\n    </table>\n  </main>'
            % (th, "\n".join(trs)))


def body_figure(d):
    return ('  <main>\n    <div class="fig"><img src="%s"></div>\n  </main>'
            % d["image"])


BODY = {"cover": body_cover, "bullets": body_bullets,
        "table": body_table, "figure": body_figure}


def render(d, theme, extra_class=""):
    """슬라이드 하나를 완성된 HTML 문서로 만든다."""
    parts = ['<!doctype html><html lang="ko"><head><meta charset="utf-8">',
             '<link rel="stylesheet" href="slides.css"></head>',
             '<body class="x2%s">' % extra_class,
             '<div class="slide theme-%s">' % theme]

    if d["kind"] != "cover":
        parts.append('  <header class="bar"><h1>%s</h1>'
                     '<span class="tag">%s</span></header>'
                     % (esc(d["title"]), esc(d.get("tag", ""))))

    parts.append(BODY[d["kind"]](d))

    if d.get("note"):
        lines = "".join("<div>%s</div>" % esc(t) for t in d["note"])
        parts.append('  <div class="note">%s</div>' % lines)

    if d["kind"] != "cover":
        parts.append('  <div class="pageno">%02d</div>' % d["no"])

    parts += ['</div>', '</body></html>', '']
    return "\n".join(parts)


def build_html():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    src = io.open(os.path.join(ROOT, "tools", "slides.css"), encoding="utf-8").read()
    io.open(os.path.join(OUT, "slides.css"), "w", encoding="utf-8").write(src)

    names = []
    for theme, _ in THEMES:
        for d in slide_content.SLIDES:
            name = "%s_%02d" % (theme, d["no"])
            io.open(os.path.join(OUT, name + ".html"), "w",
                    encoding="utf-8").write(render(d, theme))
            names.append(name)

    # 흑백 인쇄 확인용 — 불릿형 한 장만 테마별로 뽑는다
    for theme, _ in THEMES:
        d = [s for s in slide_content.SLIDES if s["kind"] == "bullets"][0]
        name = "%s_%02d_gray" % (theme, d["no"])
        io.open(os.path.join(OUT, name + ".html"), "w",
                encoding="utf-8").write(render(d, theme, " gray"))
        names.append(name)

    print("생성: figures/slides/ HTML %d개" % len(names))
    return names


# ---------------------------- 시안 pptx ----------------------------

def build_pptx():
    """렌더된 PNG 를 16:9 슬라이드에 전면으로 깔아 테마별 pptx 를 만든다.

    최종 제작 방식(방법 A)과 같은 조립이므로, 여기서 문제가 없으면
    파이프라인 전체가 검증된 것이다.
    """
    from pptx import Presentation
    from pptx.util import Inches

    made = []
    for theme, label in THEMES:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        order = ["%s_%02d" % (theme, d["no"]) for d in slide_content.SLIDES]
        order += [n for n in ["%s_04_gray" % theme] if
                  os.path.exists(os.path.join(PNG, "%s_04_gray.png" % theme))]

        for name in order:
            path = os.path.join(PNG, name + ".png")
            if not os.path.exists(path):
                print("건너뜀(PNG 없음): %s" % name)
                continue
            s = prs.slides.add_slide(prs.slide_layouts[6])
            s.shapes.add_picture(path, 0, 0, width=prs.slide_width,
                                 height=prs.slide_height)

        out = os.path.join(ROOT, "제출물", "디자인시안_%s.pptx" % label)
        prs.save(out)
        made.append(out)
        print("생성: 제출물/디자인시안_%s.pptx (%d장)" % (label, len(prs.slides._sldIdLst)))
    return made


if __name__ == "__main__":
    if "--pptx" in sys.argv:
        build_pptx()
    else:
        build_html()
