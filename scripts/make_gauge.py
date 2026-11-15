import sys, json, pandas as pd, numpy as np
src_csv, outdir = sys.argv[1], sys.argv[2]
code = open(__file__).read()
d = pd.read_csv(src_csv, parse_dates=['date']).set_index('date').close
asof = d.index[-1].strftime('%Y-%m-%d')
meta = [{"label": "make_gauge.py", "value": code, "type": "code", "lang": "python"},
        {"label": "Input", "value": "btc-usd-daily.csv (Bitstamp daily closes via github.com/rcaljouw/btc-price-history)"},
        {"label": "Data up to", "value": asof}]
def dump(name, rows): json.dump({"rows": rows, "meta": meta}, open(f"{outdir}/{name}.json", "w"))
# --- inputs (all use only past/current data) ---
ma200 = d.rolling(200).mean(); ma50 = d.rolling(50).mean()
w = d.resample('W-SUN').last()
# live 20-week average: the 19 completed weeks before this one + today's price
wkend = d.index + pd.offsets.Week(weekday=6) * 0
wkend = pd.DatetimeIndex([x if x.weekday() == 6 else x + pd.Timedelta(days=6 - x.weekday()) for x in d.index])
prev19 = w.rolling(19).sum().shift(1)
ma20w = pd.Series((prev19.reindex(wkend).values + d.values) / 20, index=d.index)
wclose = d
hi50, lo25 = d.rolling(50).max().shift(), d.rolling(25).min().shift()
pos = np.zeros(len(d))
for i in range(1, len(d)): pos[i] = 1 if d.iloc[i] > hi50.iloc[i] else (0 if d.iloc[i] < lo25.iloc[i] else pos[i-1])
brk = pd.Series(pos, index=d.index)
# weekly RSI(14), Wilder
delta = w.diff(); up = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
rsi_w = 100 - 100/(1+up/dn)  # last row = current (part) week
rsi = rsi_w.reindex(d.index, method='ffill')
rsi.iloc[-1] = rsi_w.iloc[-1]  # today's reading uses this week so far
mayer = d / ma200
ath = d.cummax(); dd = d/ath - 1
ma200w = w.rolling(200).mean().reindex(d.index, method='ffill')
lin = lambda x, a, b: ((x - a)/(b - a)*2 - 1).clip(-1, 1)   # maps a -> -1, b -> +1
comp = {
 # trend: +1 = bullish trend, -1 = bearish
 "20-week average":  ("Trend", np.where(wclose > ma20w, 1, -1), "Price above / below its 20-week average"),
 "200-day average":  ("Trend", np.where(d > ma200, 1, -1), "Price above / below its 200-day average"),
 "Golden cross":     ("Trend", np.where(ma50 > ma200, 1, -1), "50-day average above / below the 200-day"),
 "12-month momentum":("Trend", np.where(d > d.shift(365), 1, -1), "Price higher / lower than a year ago"),
 "50-day breakout":  ("Trend", np.where(brk == 1, 1, -1), "Last broke a 50-day high (in) or 25-day low (out)"),
 # value / stretch: +1 = cheap (buy zone), -1 = stretched (sell zone)
 "Mayer multiple":   ("Value", -lin(mayer, 0.8, 2.4), "Price ÷ 200-day average. Under 0.8 cheap, over 2.4 stretched"),
 "Weekly RSI":       ("Value", -lin(rsi, 30, 70), "Momentum oscillator. Under 30 oversold, over 70 overbought"),
 "Drop from peak":   ("Value", -lin(dd, -0.75, 0.0), "How far below the all-time high. Deeper = cheaper"),
}
S = pd.DataFrame({k: pd.Series(v[1], index=d.index, dtype=float) for k, v in comp.items()})
valid = d.index >= '2014-01-01'
trend = S[[k for k in comp if comp[k][0]=='Trend']].mean(axis=1)
value = S[[k for k in comp if comp[k][0]=='Value']].mean(axis=1)
score = (100*(trend + value)/2)
def zone(s): return "Strong sell" if s <= -60 else "Sell" if s <= -20 else "Neutral" if s < 20 else "Buy" if s < 60 else "Strong buy"
raw = {"20-week average": (float(wclose.iloc[-1]), float(ma20w.iloc[-1])), "200-day average": (float(d.iloc[-1]), float(ma200.iloc[-1])),
       "Golden cross": (float(ma50.iloc[-1]), float(ma200.iloc[-1])), "12-month momentum": (float(d.iloc[-1]), float(d.iloc[-366])),
       "50-day breakout": (float(d.iloc[-1]), float(hi50.iloc[-1]))}
reading = {"Mayer multiple": f"{mayer.iloc[-1]:.2f}", "Weekly RSI": f"{rsi.iloc[-1]:.0f}", "Drop from peak": f"{100*dd.iloc[-1]:.0f}%"}
comps = []
for k, (grp, _, how) in comp.items():
    v = float(S[k].iloc[-1])
    rd = reading.get(k) or ("IN" if v > 0 else "OUT")
    comps.append({"signal": k, "group": grp, "score": round(100*v), "reading": rd, "how": how,
                  "verdict": "Buy" if v >= 0.2 else "Sell" if v <= -0.2 else "Neutral"})
pd.DataFrame({'score': score, 'trend': 100*trend, 'value': 100*value}).to_csv(f"{outdir}/gauge_daily.csv")
dump("gauge_parts", comps)
cur = [{"gauge": "Overall", "score": round(float(score.iloc[-1])), "zone": zone(score.iloc[-1]), "asof": asof},
       {"gauge": "Trend", "score": round(100*float(trend.iloc[-1])), "zone": zone(100*trend.iloc[-1]), "asof": asof},
       {"gauge": "Value", "score": round(100*float(value.iloc[-1])), "zone": zone(100*value.iloc[-1]), "asof": asof}]
dump("gauge_now", cur)
# weekly history (sample each Sunday close) and forward 12-week returns per zone
wk = pd.DataFrame({"close": d, "score": score, "trend": 100*trend, "value": 100*value})[valid].resample('W-SUN').last().dropna()
wk["fwd12"] = wk.close.shift(-12)/wk.close - 1
hist = [{"week": (i - pd.Timedelta(days=6)).strftime('%Y-%m-%d'), "score": round(float(r.score)), "close": round(float(r.close))} for i, r in wk.iterrows()]
dump("gauge_history", hist)
zs = ["Strong sell", "Sell", "Neutral", "Buy", "Strong buy"]
wk["zone"] = wk.score.map(zone); ev = wk.dropna(subset=["fwd12"])
base_med = ev.fwd12.median()
bk = []
for z in zs:
    e = ev[ev.zone == z]
    bk.append({"zone": z, "weeks": int(len(e)), "median_12w_pct": round(100*float(e.fwd12.median()), 1) if len(e) else None,
               "up_12w_pct": round(100*float((e.fwd12 > 0).mean())) if len(e) else None})
bk.append({"zone": "All weeks (baseline)", "weeks": int(len(ev)), "median_12w_pct": round(100*float(base_med), 1), "up_12w_pct": round(100*float((ev.fwd12 > 0).mean()))})
dump("gauge_zones", bk)
# robustness: split halves
for lab, a, b in (("2014-19", "2014", "2019"), ("2020-now", "2020", "2026")):
    e = ev[a:b]; print(lab, e.groupby("zone").fwd12.agg(['count','median']).round(3).to_dict())
print(cur); print(pd.DataFrame(comps)[["signal","score","reading"]]); print(pd.DataFrame(bk))
