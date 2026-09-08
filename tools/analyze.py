# -*- coding: utf-8 -*-
"""
analyze.py — PEDD UART 로그 분석기

계획서 4.1.4절의 Phase 1 통과 조건을 자동으로 판정한다.
  1. 동일 시료 반복 측정의 변동계수(CV)가 10% 이내인가
  2. 최소 2종 이상의 시료가 서로 구분되는가
     (시료군 간 평균 차이 > 반복 측정 표준편차)
  3. Timeout / 이상값 발생 현황

사용법
    python tools/analyze.py data/distilled.csv data/dye.csv data/milk.csv

  파일 이름(확장자 제외)이 시료 이름으로 사용된다.
  시리얼 터미널이 남긴 로그를 시료별로 나눠 저장해두면 된다.
  헤더 행(seq,ch,...)이나 '#'으로 시작하는 행은 자동으로 무시한다.

표준 라이브러리만 사용하므로 별도 설치가 필요 없다.
"""

import sys
import os
import math

# Windows 콘솔의 기본 코드페이지(cp949)에서 한글이 깨지지 않도록 출력을 UTF-8로 고정
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass  # Python 3.6 이하 — 무시하고 진행

CV_THRESHOLD = 10.0  # 계획서 4.1.4절 예비 목표: CV 10% 이내


def parse_log(path):
    """로그 파일에서 채널별 ticks 리스트, seq별 측정 세트, timeout 횟수를 뽑아낸다.

    seq별 세트는 Phase 2의 광학 지문 벡터 [R, G, B] 를 재구성하는 데 쓴다.
    """
    channels = {}
    timeouts = {}
    by_seq = {}

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("seq"):
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue

            ch = parts[1]
            status = parts[2]

            if status == "TIMEOUT":
                timeouts[ch] = timeouts.get(ch, 0) + 1
                continue
            if status != "OK":
                continue

            try:
                seq = int(parts[0])
                ticks = int(parts[3])
            except ValueError:
                continue

            channels.setdefault(ch, []).append(ticks)
            by_seq.setdefault(seq, {})[ch] = ticks

    return channels, timeouts, by_seq


def stats(values):
    """평균, 표본표준편차, 변동계수(%)를 계산한다."""
    n = len(values)
    if n == 0:
        return None

    mean = sum(values) / n
    if n < 2:
        return {"n": n, "mean": mean, "sd": 0.0, "cv": 0.0,
                "min": min(values), "max": max(values)}

    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    sd = math.sqrt(var)
    cv = (sd / mean * 100.0) if mean else 0.0

    return {"n": n, "mean": mean, "sd": sd, "cv": cv,
            "min": min(values), "max": max(values)}


def us(ticks):
    """틱(500ns)을 마이크로초로 환산"""
    return ticks / 2.0


def channel_separation(vectors, samples_order, chans):
    """채널 부분집합 chans 에 대한 시료군 분리도를 계산한다.

    계획서 4.2.4절 — "채널 추가에 따른 시료군 분리도의 개선이 정량적으로
    확인될 것" 을 판정하기 위한 지표다.

    채널마다 방전 시간의 절대 크기가 크게 다르므로(예: Red 채널이 Blue보다
    수 배 길 수 있음), 그대로 거리를 재면 큰 채널이 결과를 지배한다.
    따라서 전체 시료를 합친 분포로 채널별 z-정규화를 먼저 수행한다.

    분리도 = min(시료군 쌍의 중심점 간 거리) / (각 군의 평균 산포 합)
    1.0 을 넘으면 두 군이 산포보다 멀리 떨어져 있다는 뜻이며, 이는 1채널
    판정에 쓴 "평균차 > 표준편차 합" 기준을 다차원으로 확장한 것이다.
    """
    # 1) 시료별 벡터 수집 (요청한 채널이 모두 있는 seq만 사용)
    groups = {}
    for name in samples_order:
        pts = []
        for seq in sorted(vectors.get(name, {})):
            row = vectors[name][seq]
            if all(c in row for c in chans):
                pts.append([float(row[c]) for c in chans])
        if pts:
            groups[name] = pts

    if len(groups) < 2:
        return None

    # 2) 채널별 z-정규화 (전체 시료 통합 분포 기준)
    ndim = len(chans)
    pooled = [v for pts in groups.values() for v in pts]
    means, sds = [], []
    for d in range(ndim):
        col = [p[d] for p in pooled]
        m = sum(col) / len(col)
        var = sum((x - m) ** 2 for x in col) / (len(col) - 1) if len(col) > 1 else 0.0
        sd = math.sqrt(var)
        means.append(m)
        sds.append(sd if sd > 0 else 1.0)

    norm = {}
    for name, pts in groups.items():
        norm[name] = [[(p[d] - means[d]) / sds[d] for d in range(ndim)] for p in pts]

    # 3) 군별 중심점과 평균 산포
    cent, spread = {}, {}
    for name, pts in norm.items():
        c = [sum(p[d] for p in pts) / len(pts) for d in range(ndim)]
        cent[name] = c
        dists = [math.sqrt(sum((p[d] - c[d]) ** 2 for d in range(ndim))) for p in pts]
        spread[name] = sum(dists) / len(dists)

    # 4) 가장 가까운 군 쌍이 곧 분리도의 병목이다
    names = sorted(cent)
    worst = None
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            d = math.sqrt(sum((cent[a][k] - cent[b][k]) ** 2 for k in range(ndim)))
            denom = spread[a] + spread[b]
            ratio = (d / denom) if denom > 0 else float("inf")
            if worst is None or ratio < worst[0]:
                worst = (ratio, a, b)

    return {"ratio": worst[0], "pair": (worst[1], worst[2]), "n_groups": len(groups)}


def main(paths):
    samples = {}   # 시료명 -> {채널: 통계}
    vectors = {}   # 시료명 -> {seq: {채널: ticks}}
    all_timeouts = {}

    for path in paths:
        if not os.path.exists(path):
            print("[건너뜀] 파일 없음: %s" % path)
            continue

        name = os.path.splitext(os.path.basename(path))[0]
        channels, timeouts, by_seq = parse_log(path)

        if not channels:
            print("[건너뜀] 유효한 측정값 없음: %s" % path)
            continue

        samples[name] = {ch: stats(v) for ch, v in channels.items()}
        vectors[name] = by_seq
        if timeouts:
            all_timeouts[name] = timeouts

    if not samples:
        print("분석할 데이터가 없습니다.")
        return 1

    # ---- 1. 채널별 재현성 ----
    print("=" * 74)
    print("1. 반복 측정 재현성  (통과 기준: CV <= %.1f%%)" % CV_THRESHOLD)
    print("=" * 74)
    print("%-14s %-6s %4s %12s %10s %8s  %s"
          % ("시료", "채널", "n", "평균(us)", "표준편차", "CV(%)", "판정"))
    print("-" * 74)

    cv_fail = 0
    cv_unjudged = 0
    for name in sorted(samples):
        for ch in sorted(samples[name]):
            s = samples[name][ch]
            # 1회 측정은 표준편차가 정의되지 않는다. sd=0 이 나오므로 그냥
            # 비교하면 CV 0% 로 "통과" 가 찍히는데, 재현성을 전혀 확인하지
            # 않은 것이라 통과로 세면 안 된다. 별도로 표시하고 종합 판정에서
            # 미달로 취급한다.
            if s["n"] < 2:
                cv_unjudged += 1
                print("%-14s %-6s %4d %12.1f %10s %8s  %s"
                      % (name, ch, s["n"], us(s["mean"]), "-", "-",
                         "판정 불가 (2회 이상 필요)"))
                continue
            ok = s["cv"] <= CV_THRESHOLD
            if not ok:
                cv_fail += 1
            print("%-14s %-6s %4d %12.1f %10.1f %8.2f  %s"
                  % (name, ch, s["n"], us(s["mean"]), us(s["sd"]),
                     s["cv"], "통과" if ok else "미달"))

    # ---- 2. 시료군 간 분리도 ----
    print()
    print("=" * 74)
    print("2. 시료군 간 분리도  (통과 기준: 평균 차이 > 두 시료 표준편차의 합)")
    print("=" * 74)

    names = sorted(samples)
    all_channels = sorted({ch for n in names for ch in samples[n]})
    separated_pairs = 0

    if len(names) < 2:
        print("시료가 1종뿐이라 분리도를 계산할 수 없습니다.")
        print("증류수/착색수/탁도수 로그를 함께 넘겨주세요.")
    else:
        print("%-6s %-13s %-13s %12s %10s %8s  %s"
              % ("채널", "시료 A", "시료 B", "평균차(us)", "SD합(us)",
                 "비율", "판정"))
        print("-" * 74)

        for ch in all_channels:
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = names[i], names[j]
                    if ch not in samples[a] or ch not in samples[b]:
                        continue

                    sa, sb = samples[a][ch], samples[b][ch]
                    diff = abs(sa["mean"] - sb["mean"])
                    sdsum = sa["sd"] + sb["sd"]
                    ratio = (diff / sdsum) if sdsum > 0 else float("inf")
                    ok = ratio > 1.0
                    if ok and ch != "DARK":
                        separated_pairs += 1

                    print("%-6s %-13s %-13s %12.1f %10.1f %8.2f  %s"
                          % (ch, a, b, us(diff), us(sdsum), ratio,
                             "구분됨" if ok else "구분 안 됨"))

    # ---- 3. 채널 추가에 따른 분리도 개선 (Phase 2) ----
    have_rgb = all(any(ch == c for n in names for ch in samples[n])
                   for c in ("R", "G", "B"))
    phase2_ok = None

    if have_rgb and len(names) >= 2:
        print()
        print("=" * 74)
        print("3. 채널 추가에 따른 분리도 개선  (계획서 4.2.4절 Phase 2 성공 기준)")
        print("=" * 74)
        print("%-12s %10s %10s  %-26s %s"
              % ("채널 구성", "분리도", "개선", "가장 가까운 시료 쌍", "판정"))
        print("-" * 74)

        subsets = [("R", ["R"]), ("RG", ["R", "G"]), ("RGB", ["R", "G", "B"])]
        prev = None
        results = []

        for label, chans in subsets:
            res = channel_separation(vectors, names, chans)
            if res is None:
                print("%-12s %10s" % (label, "데이터 부족"))
                continue

            delta = "—" if prev is None else "%+.2f" % (res["ratio"] - prev)
            verdict = "구분됨" if res["ratio"] > 1.0 else "구분 안 됨"
            print("%-12s %10.2f %10s  %-26s %s"
                  % (label, res["ratio"], delta,
                     "%s / %s" % res["pair"], verdict))
            results.append((label, res["ratio"]))
            prev = res["ratio"]

        print()
        print("  분리도 = 가장 가까운 시료군 쌍의 중심점 거리 / 두 군의 산포 합")
        print("  (채널별 z-정규화 후 계산. 1.0 초과면 산포보다 멀리 떨어져 있음)")

        if len(results) >= 2:
            improved = results[-1][1] > results[0][1]
            phase2_ok = improved and results[-1][1] > 1.0
            print()
            print("  R(%.2f) → RGB(%.2f) : %s"
                  % (results[0][1], results[-1][1],
                     "채널 추가로 분리도 개선됨" if improved
                     else "채널을 늘려도 개선되지 않음"))
            if not improved:
                print("  → 기여도가 낮은 파장은 최종 구성에서 제외를 검토하세요 (계획서 3.3절)")

    # ---- 4. Timeout / 이상값 ----
    print()
    print("=" * 74)
    print("4. Timeout 및 이상값")
    print("=" * 74)
    if all_timeouts:
        for name in sorted(all_timeouts):
            for ch, cnt in sorted(all_timeouts[name].items()):
                print("  %s / %s : TIMEOUT %d회" % (name, ch, cnt))
    else:
        print("  TIMEOUT 없음")

    # 오버플로우 경계 이상값 탐지 (계획서 3.7절 구현 메모)
    print()
    print("  [참고] 평균에서 3 표준편차를 벗어난 값:")
    found_outlier = False
    for name in sorted(samples):
        for ch in sorted(samples[name]):
            s = samples[name][ch]
            if s["sd"] == 0:
                continue
            lo = s["mean"] - 3 * s["sd"]
            hi = s["mean"] + 3 * s["sd"]
            if s["min"] < lo or s["max"] > hi:
                found_outlier = True
                print("    %s / %s : 범위 %.1f ~ %.1f us (평균 %.1f us)"
                      % (name, ch, us(s["min"]), us(s["max"]), us(s["mean"])))
    if not found_outlier:
        print("    없음")

    # ---- 5. Phase 1 종합 판정 ----
    print()
    print("=" * 74)
    print("5. 종합 판정")
    print("=" * 74)
    print("  [Phase 1 — 계획서 4.1.4절]")
    c1 = (cv_fail == 0 and cv_unjudged == 0)
    c2 = (separated_pairs >= 1)
    if cv_fail:
        cv_msg = "미달 (%d개 채널)" % cv_fail
    elif cv_unjudged:
        cv_msg = "판정 불가 (%d개 채널이 1회 측정)" % cv_unjudged
    else:
        cv_msg = "통과"
    print("  조건 1. 재현성 CV <= %.0f%%          : %s" % (CV_THRESHOLD, cv_msg))
    print("  조건 2. 시료 2종 이상 구분           : %s"
          % ("통과" if c2 else "미달"))
    print("  조건 3. Overflow / Timeout 정상 동작 : 로그를 직접 확인할 것")
    print()
    if phase2_ok is not None:
        print("  [Phase 2 — 계획서 4.2.4절]")
        print("    2개 이상 채널에서 시료군 구분 + 채널 추가로 분리도 개선")
        print("                                       : %s"
              % ("통과" if phase2_ok else "미달"))
        print()

    if c1 and c2 and phase2_ok:
        msg = "Phase 1·2 통과. 예선 보고서 작성으로 진행하세요."
    elif c1 and c2 and phase2_ok is None:
        msg = "Phase 1 조건 1, 2 통과. 조건 3 확인 후 Phase 2로 진행."
    else:
        msg = "미달 항목이 있습니다. 계획서 4.5절 실패 대응표를 참조하세요."
    print("  => %s" % msg)

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))
