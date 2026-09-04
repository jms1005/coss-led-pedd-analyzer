# -*- coding: utf-8 -*-
"""제작 관련 마크다운 문서 -> A4 PDF, 그리고 제작 순서대로 묶은 한 권.

만드는 것 (모두 `제작문서/` 폴더):
  00_제작순서표.pdf    전체 문서를 제작 순서로 나열한 표지 (쪽 번호 포함)
  01~12_*.pdf          문서별 낱장 PDF (파일명 앞 번호 = 제작 순서)
  제작문서_전체.pdf     위를 순서대로 이어붙인 한 권

기존 tools/make_*_pdf.sh 와 같은 방식이다. Chrome 헤드리스 인쇄를 쓰고,
한글이 섞인 경로에서 file:// URL 이 깨지므로 임시 ASCII 경로에서 변환한 뒤
결과만 되가져온다.

실행:  python tools/make_docs_pdf.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "제작문서"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

# (순번, 출력 이름, 종류, 원본 경로, 단계, 한 줄 설명)
#   md  = 마크다운을 이번에 변환한다
#   pdf = 이미 다른 스크립트가 만들어 둔 PDF 를 순서에 맞춰 가져온다
DOCS = [
  ("01", "구매목록", "md", "구매목록.md",
   "1. 주문", "무엇을 왜 사는지 — 부품별 판단 근거"),
  ("02", "구매목록_장바구니용", "pdf", "docs/구매목록.pdf",
   "1. 주문", "주문할 때 보는 A4 한 장 요약"),
  ("03", "차광챔버_제작", "md", "docs/차광챔버_제작.md",
   "2. 부품 기다리는 동안", "치수와 만드는 법의 출처 문서"),
  ("04", "제작도면", "pdf", "docs/제작도면.pdf",
   "2. 부품 기다리는 동안", "보면서 자르는 A4 6장 (2·3·4장은 1:1 실척)"),
  ("05", "제작도면_인쇄설정", "md", "figures/build/README.md",
   "2. 부품 기다리는 동안", "실척 템플릿을 배율 100%로 뽑는 법"),
  ("06", "회로도", "pdf", "제출물/나_회로도.pdf",
   "3. 부품 도착 후 배선", "전체 결선의 기준 (A3 1장)"),
  ("07", "배선도", "pdf", "docs/배선도.pdf",
   "3. 부품 도착 후 배선", "브레드보드 몇 번 구멍에 꽂는지 (A4 4장)"),
  ("08", "배선도_사용법", "md", "figures/wiring/README.md",
   "3. 부품 도착 후 배선", "배선도를 어떻게 보는지, 실척이 아닌 이유"),
  ("09", "펌웨어_셋업", "md", "firmware/README.md",
   "4. 펌웨어 올리기", "Microchip Studio 설정과 업로드 순서"),
  ("10", "측정_프로토콜", "md", "docs/측정_프로토콜.md",
   "5. 측정 당일", "인쇄해서 옆에 두고 체크하는 순서표"),
  ("11", "측정데이터_기록규칙", "md", "data/README.md",
   "5. 측정 당일", "로그 파일 이름 규칙과 함께 남길 메모"),
  ("12", "동영상_촬영_시나리오", "md", "docs/동영상_촬영_시나리오.md",
   "6. 제출물 만들기", "제출물 「라. 동작 동영상」 촬영 구성"),
]

CSS = """
@page { size: A4; margin: 16mm 15mm 15mm 15mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
       font-size: 10.5pt; line-height: 1.65; color: #1a1a1a; }
.hdr { border-bottom: 2.5px solid #1a1a1a; padding-bottom: 6px; margin-bottom: 18px;
       display: flex; align-items: baseline; gap: 10px; }
.hdr .no { font-size: 15pt; font-weight: 700; letter-spacing: -0.5px; }
.hdr .stage { font-size: 9pt; font-weight: 700; color: #fff; background: #1a1a1a;
              padding: 2px 8px; border-radius: 3px; }
.hdr .src { margin-left: auto; font-size: 8.5pt; color: #777;
            font-family: Consolas, monospace; }
h1 { font-size: 19pt; margin: 0 0 4px; letter-spacing: -0.5px; line-height: 1.3; }
h2 { font-size: 14pt; margin: 22px 0 8px; padding-bottom: 4px;
     border-bottom: 1px solid #d5d5d5; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 16px 0 6px; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin: 12px 0 4px; page-break-after: avoid; }
p, li { orphans: 2; widows: 2; }
ul, ol { padding-left: 22px; margin: 6px 0; }
li { margin: 2px 0; }
code { font-family: Consolas, "D2Coding", monospace; font-size: 9.3pt;
       background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }
pre { background: #f6f6f6; border: 1px solid #e0e0e0; border-left: 3px solid #888;
      padding: 9px 11px; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 9pt; line-height: 1.45;
           white-space: pre-wrap; word-break: break-all; }
blockquote { margin: 10px 0; padding: 8px 12px; background: #fbf7e8;
             border-left: 3px solid #c9a227; }
blockquote p { margin: 4px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.3pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 4px 7px; text-align: left;
         vertical-align: top; }
th { background: #efefef; font-weight: 700; }
hr { border: 0; border-top: 1px solid #ddd; margin: 18px 0; }
a { color: #1a1a1a; text-decoration: none; }
strong { font-weight: 700; }
"""

INDEX_CSS = """
@page { size: A4; margin: 15mm 14mm; }
body { margin: 0; font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
       font-size: 10pt; color: #1a1a1a; }
h1 { font-size: 22pt; margin: 0 0 2px; letter-spacing: -1px; }
.sub { color: #666; font-size: 9.5pt; margin-bottom: 4px; }
.rule { border-top: 2.5px solid #1a1a1a; margin: 10px 0 16px; }
.note { background: #fbf7e8; border-left: 3px solid #c9a227; padding: 8px 11px;
        font-size: 9pt; line-height: 1.6; margin-bottom: 16px; }
.stage { font-size: 11pt; font-weight: 700; margin: 16px 0 6px;
         padding: 3px 9px; background: #1a1a1a; color: #fff; display: inline-block;
         border-radius: 3px; }
table { border-collapse: collapse; width: 100%; font-size: 9.3pt; }
th { background: #efefef; border: 1px solid #ccc; padding: 4px 7px;
     text-align: left; font-size: 8.5pt; }
td { border: 1px solid #ccc; padding: 5px 7px; vertical-align: top; }
.c-chk { width: 8mm; text-align: center; font-size: 12pt; color: #999; }
.c-no { width: 9mm; text-align: center; font-weight: 700; }
.c-nm { font-weight: 700; }
.c-nm span { display: block; font-weight: 400; color: #666; font-size: 8.5pt;
             margin-top: 1px; }
.c-pg { width: 20mm; text-align: center; font-family: Consolas, monospace;
        font-size: 9pt; }
.c-fl { width: 46mm; font-family: Consolas, monospace; font-size: 8pt;
        color: #666; word-break: break-all; }
.foot { margin-top: 18px; padding-top: 8px; border-top: 1px solid #ddd;
        font-size: 8.5pt; color: #666; line-height: 1.7; }
"""


def md_to_html(src, no, stage, title_hint):
  """마크다운 한 편을 인쇄용 HTML 한 편으로 바꾼다."""
  text = src.read_text(encoding="utf-8")
  # 체크박스는 markdown 기본 확장이 처리하지 못하므로 기호로 바꿔둔다
  text = re.sub(r"^(\s*[-*] )\[ \] ", r"\1☐ ", text, flags=re.M)
  text = re.sub(r"^(\s*[-*] )\[[xX]\] ", r"\1☑ ", text, flags=re.M)
  body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
  rel = src.relative_to(ROOT).as_posix()
  return (
    '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
    f"<title>{no} {title_hint}</title><style>{CSS}</style></head><body>"
    f'<div class="hdr"><span class="no">{no}</span>'
    f'<span class="stage">{stage}</span>'
    f'<span class="src">{rel}</span></div>'
    f"{body}</body></html>"
  )


def index_html(rows, total):
  """제작 순서표 한 장. rows = (순번, 이름, 설명, 단계, 쪽수, 시작쪽, 파일명)"""
  out, cur = [], None
  for no, name, desc, stage, pages, start, fname in rows:
    if stage != cur:
      if cur is not None:
        out.append("</tbody></table>")
      cur = stage
      out.append(f'<div class="stage">{stage}</div>')
      out.append('<table><thead><tr><th></th><th>순</th><th>문서</th>'
                 '<th>묶음 쪽</th><th>낱장 파일</th></tr></thead><tbody>')
    span = str(start) if pages == 1 else f"{start}–{start + pages - 1}"
    out.append(f'<tr><td class="c-chk">☐</td><td class="c-no">{no}</td>'
               f'<td class="c-nm">{name}<span>{desc}</span></td>'
               f'<td class="c-pg">{span}</td><td class="c-fl">{fname}</td></tr>')
  out.append("</tbody></table>")
  return (
    '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
    f"<title>제작 순서표</title><style>{INDEX_CSS}</style></head><body>"
    "<h1>제작 순서표</h1>"
    '<div class="sub">LED PEDD 액체 광학 분석기 · 부품 주문부터 동영상 촬영까지</div>'
    '<div class="rule"></div>'
    '<div class="note"><b>순서대로 보는 두 가지 방법.</b> '
    "① <b>제작문서_전체.pdf</b> 한 권을 열고 아래 「묶음 쪽」으로 찾아간다 "
    f"(이 순서표가 1쪽, 본문은 그 뒤부터, 전체 {total}쪽). "
    "② <b>제작문서</b> 폴더를 이름순으로 정렬하면 파일명 앞 번호가 그대로 제작 순서다.<br>"
    "<b>인쇄할 때.</b> 04 제작도면의 2·3·4장은 <b>1:1 실척 재단 템플릿</b>이므로 "
    "반드시 배율 100%(「실제 크기」)로 뽑는다. 자세한 설정은 05 문서에 있다.</div>"
    + "".join(out) +
    '<div class="foot">이 순서표와 낱장 PDF 는 '
    "<code>python tools/make_docs_pdf.py</code> 가 만든다. 내용을 고칠 때는 "
    "PDF 가 아니라 원본 마크다운을 고치고 다시 실행한다.<br>"
    "04 제작도면 · 07 배선도 · 06 회로도 는 각각 <code>make_build_pdf.sh</code> · "
    "<code>make_wiring_pdf.sh</code> · <code>make_pdf.sh</code> 가 만든 것을 "
    "순서에 맞게 가져온 것이다.</div></body></html>"
  )


def render(html, tmp, stem):
  """HTML 한 편을 Chrome 헤드리스로 A4 PDF 로 뽑는다."""
  src = tmp / f"{stem}.html"
  pdf = tmp / f"{stem}.pdf"
  src.write_text(html, encoding="utf-8")
  subprocess.run(
    [str(CHROME), "--headless", "--disable-gpu", "--no-sandbox",
     "--no-pdf-header-footer", f"--print-to-pdf={pdf}", src.as_uri()],
    check=True, capture_output=True)
  if not pdf.exists():
    sys.exit(f"오류: {stem} PDF 생성 실패")
  return pdf


def main():
  if not CHROME.exists():
    sys.exit(f"오류: Chrome 을 찾을 수 없습니다 — {CHROME}")
  OUT.mkdir(exist_ok=True)
  for old in OUT.glob("*.pdf"):
    old.unlink()

  tmp = Path(tempfile.mkdtemp(prefix="pedd_docs_"))  # ASCII 경로여야 한다
  try:
    parts, rows = [], []
    for no, name, kind, rel, stage, desc in DOCS:
      src = ROOT / rel
      if not src.exists():
        sys.exit(f"오류: 원본이 없습니다 — {rel}")
      fname = f"{no}_{name}.pdf"
      dst = OUT / fname
      if kind == "md":
        shutil.copy(render(md_to_html(src, no, stage, name), tmp, f"d{no}"), dst)
      else:
        shutil.copy(src, dst)
      pages = len(PdfReader(str(dst)).pages)
      parts.append(dst)
      rows.append([no, name, desc, stage, pages, 0, fname])
      print(f"  {no} {name:<22} {pages:>2}쪽   ({rel})")

    # 순서표 쪽수를 알아야 본문 시작 쪽을 적을 수 있으므로 두 번 뽑는다
    draft = render(index_html([tuple(r) for r in rows], 0), tmp, "idx0")
    offset = len(PdfReader(str(draft)).pages)
    pos = offset + 1
    for r in rows:
      r[5] = pos
      pos += r[4]
    total = pos - 1
    idx = OUT / "00_제작순서표.pdf"
    shutil.copy(render(index_html([tuple(r) for r in rows], total), tmp, "idx1"), idx)
    if len(PdfReader(str(idx)).pages) != offset:
      print("  주의: 순서표 쪽수가 바뀌어 묶음 쪽 번호가 어긋날 수 있습니다")

    writer = PdfWriter()
    for p in [idx] + parts:
      writer.append(str(p))
    book = OUT / "제작문서_전체.pdf"
    with book.open("wb") as f:
      writer.write(f)

    print(f"\n생성: 제작문서/ 낱장 {len(parts)}개 + 00_제작순서표.pdf")
    print(f"생성: 제작문서/제작문서_전체.pdf ({len(PdfReader(str(book)).pages)}쪽)")
  finally:
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
  main()
