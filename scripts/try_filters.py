#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, subprocess, time, csv, re, json
from pathlib import Path

LOG = Path("automatic_hybrid_bot.log")
RUNTIME = Path(".runtime")
CYCLE_FILE = RUNTIME / "cycle_events.ndjson"
LAST_FILE = RUNTIME / "last_cycle.json"
CSV_OUT = RUNTIME / "filter_grid_results.csv"

PALAUTETTU_RE = re.compile(r"Palautettu\s+(\d+)\s+kandidattia")

def parse_args():
    p = argparse.ArgumentParser("Grid tuning for discovery filters")
    p.add_argument("--liqs", default="800,1000,1200,1500", help="min_liq_fresh_usd list, comma-separated")
    p.add_argument("--top10", default="0.98,0.985,0.99,0.995", help="max_top10_share_fresh list")
    p.add_argument("--score", default="0.45,0.50,0.52,0.55", help="score_threshold list")
    p.add_argument("--cycles", type=int, default=3, help="TEST_MAX_CYCLES per run")
    p.add_argument("--timeout", type=int, default=180, help="subprocess timeout seconds")
    return p.parse_args()

def read_cycle_hot_sum():
    if not CYCLE_FILE.exists():
        return 0
    hot_sum = 0
    try:
        with CYCLE_FILE.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    j = json.loads(line)
                    if j.get("evt") == "cycle_end":
                        hot_sum += int(j.get("hot") or 0)
                except Exception:
                    continue
    except Exception:
        pass
    return hot_sum

def read_candidates_sum(since_len: int) -> int:
    """Summaa 'Palautettu N kandidaattia' uudet rivit logista lukemalla vain lopun (since_len offset)."""
    if not LOG.exists():
        return 0
    try:
        data = LOG.read_text(encoding="utf-8")
        tail = data[since_len:]
        total = 0
        for m in PALAUTETTU_RE.finditer(tail):
            total += int(m.group(1))
        return total
    except Exception:
        return 0

class contextlib_suppress:
    def __enter__(self): return self
    def __exit__(self, *exc): return True

def run_combo(liq: float, top10: float, score: float, cycles: int, timeout: int):
    # nollaa runtime-tiedostot
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with contextlib_suppress(): LAST_FILE.unlink()
    with contextlib_suppress(): CYCLE_FILE.unlink()

    prev_len = 0
    if LOG.exists():
        prev_len = LOG.stat().st_size

    env = os.environ.copy()
    env["TEST_ALIGN_NOW"] = "1"
    env["TEST_MAX_CYCLES"] = str(cycles)
    env["TRADING_ENABLED"] = "true"
    env["TRADING_PAPER_TRADE"] = "true"
    env["METRICS_ENABLED"] = "0"
    env["DISCOVERY_MIN_LIQ_FRESH_USD"] = str(liq)
    env["DISCOVERY_MAX_TOP10_SHARE_FRESH"] = str(top10)
    env["DISCOVERY_SCORE_THRESHOLD"] = str(score)

    t0 = time.time()
    try:
        subprocess.run(
            ["python3", "automatic_hybrid_bot.py"],
            env=env, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        pass
    dur = time.time() - t0

    hot = read_cycle_hot_sum()
    cand = read_candidates_sum(prev_len)
    return {"hot": hot, "cand": cand, "duration": round(dur, 1)}

def main():
    args = parse_args()
    liqs = [float(x) for x in args.liqs.split(",") if x.strip()]
    top10s = [float(x) for x in args.top10.split(",") if x.strip()]
    scores = [float(x) for x in args.score.split(",") if x.strip()]

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    write_header = not CSV_OUT.exists()
    with CSV_OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["min_liq_fresh_usd","max_top10_share_fresh","score_threshold","hot_total","candidates_total","duration_s","ts"])
        best = []
        for liq in liqs:
            for top10 in top10s:
                for score in scores:
                    res = run_combo(liq, top10, score, args.cycles, args.timeout)
                    row = [liq, top10, score, res["hot"], res["cand"], res["duration"], time.strftime("%Y-%m-%d %H:%M:%S")]
                    w.writerow(row); f.flush()
                    best.append(row)
                    print(f"[GRID] liq={liq} top10={top10} score={score} → hot={res['hot']} cand={res['cand']} ({res['duration']}s)")

    # tulosta TOP-kombot
    def keyer(r): return (int(r[3]), int(r[4]))  # hot, candidates
    best.sort(key=keyer, reverse=True)
    print("\n=== TOP 10 ===")
    for r in best[:10]:
        print(f"liq={r[0]} top10={r[1]} score={r[2]}  hot={r[3]} cand={r[4]}  dur={r[5]}s")

if __name__ == "__main__":
    main()
