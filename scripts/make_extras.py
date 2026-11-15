import sys, json, pandas as pd, numpy as np
src_csv, gauge_csv, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
code = open(__file__).read()
d = pd.read_csv(src_csv, parse_dates=['date']).set_index('date').close
g = pd.read_csv(gauge_csv, parse_dates=['date']).set_index('date')
asof = d.index[-1].strftime('%Y-%m-%d'); price = float(d.iloc[-1])
meta = [{"label": "make_extras.py", "value": code, "type": "code", "lang": "python"},
        {"label": "Input", "value": "btc-usd-daily.csv (Bitstamp) and gauge_daily.csv (from make_gauge.py)"},
        {"label": "Data up to", "value": asof}]
def dump(name, rows): json.dump({"rows": rows, "meta": meta}, open(f"{outdir}/{name}.json", "w"))
def zone(s): return "Strong sell" if s <= -60 else "Sell" if s <= -20 else "Neutral" if s < 20 else "Buy" if s < 60 else "Strong buy"
MULT = {"Strong sell": 0.25, "Sell": 0.5, "Neutral": 1.0, "Buy": 1.5, "Strong buy": 2.0}
# ---------- smart buying: buy on the first day of each month, using the gauge as of the day before ----------
def run(start, col):
    days = d[start:].groupby(d[start:].index.to_period('M')).head(1).index
    spent = btc = 0.0
    for t in days:
        m = 1.0 if col is None else MULT[zone(g[col].shift(1).loc[t])]
        amt = 100 * m; spent += amt; btc += amt / d.loc[t]
    return spent, btc
dca = []
for per, start in (("2014–now", "2014-01-01"), ("2020–now", "2020-01-01")):
    for name, col in (("Same amount every month", None), ("More when gauge says Buy", "score"), ("More when Value says Buy", "value")):
        spent, btc = run(start, col)
        dca.append({"plan": name, "period": per, "spent": round(spent), "btc": round(btc, 4), "avg_cost": round(spent / btc),
                    "value_now": round(btc * price), "multiple": round(btc * price / spent, 2)})
dump("dca", dca)
# ---------- drawdowns: every fall of 50%+ from a peak ----------
peak = d.cummax(); dd = d / peak - 1
falls = []; in_fall = False
for t, v in dd.items():
    if not in_fall and v <= -0.5: in_fall = True; st = t
    if in_fall and v == 0:
        seg = dd[st:t]; lo = seg.idxmin()
        pk = d[:st].idxmax()
        falls.append({"fall": (f"{pk.year}" if pk.year == lo.year else f"{pk.year}–{lo.year}"), "peak_date": pk.strftime('%b %Y'), "low_date": lo.strftime('%b %Y'), "drop_pct": round(100 * float(seg.min())), "status": "Recovered"})
        in_fall = False
if in_fall or dd.iloc[-1] < -0.3:
    st = d[:dd.index[-1]][dd == 0].index[-1]; seg = dd[st:]; lo = seg.idxmin()
    falls.append({"fall": f"{st.year}–now", "peak_date": st.strftime('%b %Y'), "low_date": lo.strftime('%b %Y'), "drop_pct": round(100 * float(seg.min())), "status": "Ongoing"})
dump("drawdowns", falls)
# ---------- halving cycle clock ----------
halvings = [("2012", "2012-11-28"), ("2016", "2016-07-09"), ("2020", "2020-05-11"), ("2024", "2024-04-20")]
cyc = []; summ = []
for name, h in halvings:
    h = pd.Timestamp(h); base = float(d.loc[h])
    seg = d[h:h + pd.Timedelta(days=1460)]
    for day in range(0, len(seg), 7):
        cyc.append({"cycle": name, "day": day, "multiple": round(float(seg.iloc[day] / base), 3)})
    if name == "2024": cyc.append({"cycle": name, "day": len(seg) - 1, "multiple": round(float(seg.iloc[-1] / base), 3)})
    pk = seg.idxmax()
    summ.append({"cycle": name, "halving_price": round(base), "peak_day": int((pk - h).days), "peak_multiple": round(float(seg.max() / base), 1),
                 "day_now_equiv": int(len(seg) - 1) if name == "2024" else None,
                 "multiple_at_same_day": round(float(seg.iloc[min(len(d[pd.Timestamp('2024-04-20'):]) - 1, len(seg) - 1)] / base), 2)})
dump("cycles", cyc); dump("cycle_summary", summ)
print(pd.DataFrame(dca)); print(pd.DataFrame(falls)); print(pd.DataFrame(summ))
