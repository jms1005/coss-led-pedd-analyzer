"""phase4.cproj 의 ItemGroup 에 common/ 소스를 등록한다.

사용법: python tools/add_sources.py classify.c classify.h ...
이미 등록된 파일은 건너뛴다.
"""
import io
import os
import sys

CPROJ = os.path.join('firmware', '04_phase4', 'phase4.cproj')
BS = chr(92)
NL = chr(10)


def entry(name):
    return (
        '    <Compile Include="..' + BS + 'common' + BS + name + '">' + NL +
        '      <SubType>compile</SubType>' + NL +
        '      <Link>' + name + '</Link>' + NL +
        '    </Compile>' + NL
    )


def main(names):
    s = io.open(CPROJ, encoding='utf-8-sig', newline='').read()
    added = []
    block = ''
    for n in names:
        if ('<Link>' + n + '</Link>') in s:
            continue
        block += entry(n)
        added.append(n)
    if not added:
        print('추가할 항목 없음')
        return
    anchor = '  </ItemGroup>'
    if anchor not in s:
        raise SystemExit('ItemGroup 앵커를 찾지 못했다')
    # 파일에 CRLF 가 섞여 있으므로 앵커도 실제 표기를 따른다.
    crlf_anchor = '  </ItemGroup>' + chr(13) + chr(10)
    if crlf_anchor in s:
        s = s.replace(crlf_anchor, block.replace(NL, chr(13) + chr(10)) + crlf_anchor, 1)
    else:
        s = s.replace(anchor, block + anchor, 1)
    io.open(CPROJ, 'w', encoding='utf-8-sig', newline='').write(s)
    print('등록: %s' % ' '.join(added))


if __name__ == '__main__':
    main(sys.argv[1:])
