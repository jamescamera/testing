import json
names = ["make_dash_data.py", "make_gauge.py", "make_levels.py", "make_extras.py"]
scripts = {n: open(f"/home/claude/scripts/{n}").read() for n in names}
runner = r'''
# BTC dashboard weekly refresh kit. Usage:
#   python3 -I refresh_kit.py BTC_DAILY_CSV FGI_4H_CSV OUTDIR [PREVDIR]
# Writes every dashboard JSON into OUTDIR and alerts.txt (what flipped vs PREVDIR).
import sys, os, json, subprocess
SCRIPTS = __SCRIPTS__
btc, fgi, out = sys.argv[1], sys.argv[2], sys.argv[3]
prev = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
sd = os.path.join(os.path.dirname(os.path.abspath(out)), "kit_scripts"); os.makedirs(sd, exist_ok=True)
for n, code in SCRIPTS.items(): open(os.path.join(sd, n), "w").write(code)
run = lambda *a: subprocess.run([sys.executable, "-I", *a], check=True, stdout=subprocess.DEVNULL)
run(os.path.join(sd, "make_dash_data.py"), btc, out)
run(os.path.join(sd, "make_gauge.py"), btc, out)
run(os.path.join(sd, "make_levels.py"), btc, fgi, out)
run(os.path.join(sd, "make_extras.py"), btc, os.path.join(out, "gauge_daily.csv"), out)
rows = lambda d, n: json.load(open(os.path.join(d, n + ".json")))["rows"]
alerts = []
if prev:
    def safe(n):
        try: return rows(prev, n)
        except Exception: return None
    old = safe("signals")
    if old:
        o = {r["rule"]: r["state"] for r in old}
        for r in rows(out, "signals"):
            if r["rule"] in o and o[r["rule"]] != r["state"]: alerts.append(f"{r['rule']} flipped {o[r['rule']]} -> {r['state']}")
    old = safe("gauge_now")
    if old:
        o = {r["gauge"]: r["zone"] for r in old}
        for r in rows(out, "gauge_now"):
            if r["gauge"] in o and o[r["gauge"]] != r["zone"]: alerts.append(f"{r['gauge']} gauge moved {o[r['gauge']]} -> {r['zone']} (score {r['score']})")
    old = safe("levels")
    if old:
        o = {r["level"]: r["side"] for r in old}
        for r in rows(out, "levels"):
            if r["level"] in ("200-week average", "200-day average", "20-week average", "52-week low") and r["level"] in o and o[r["level"]] != r["side"]:
                alerts.append(f"Price crossed the {r['level']} (now {'below' if r['side'] == 'Above' else 'above'} it, level ${r['price']:,})")
    old = safe("fgi_now")
    if old and old[0]["label"] != rows(out, "fgi_now")[0]["label"]:
        alerts.append(f"Fear & Greed moved {old[0]['label']} -> {rows(out, 'fgi_now')[0]['label']}")
g = {r["gauge"]: r for r in rows(out, "gauge_now")}; s = rows(out, "signals"); f = rows(out, "fgi_now")[0]
summary = (f"BTC ${s[0]['price']:,} (close {s[0]['asof']}). Gauge {g['Overall']['zone']} ({g['Overall']['score']:+}): trend {g['Trend']['zone']}, value {g['Value']['zone']}. "
           f"{sum(r['in'] for r in s)}/5 trend rules IN. Fear & Greed {f['index']} ({f['label']}).")
open(os.path.join(out, "alerts.txt"), "w").write("\n".join(alerts))
print("SUMMARY:", summary)
print("ALERTS:", "; ".join(alerts) if alerts else "none")
'''.replace("__SCRIPTS__", json.dumps(scripts))
open("/home/claude/work/refresh_kit.py", "w").write(runner)
