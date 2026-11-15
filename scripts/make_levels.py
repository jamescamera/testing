import sys, json, pandas as pd, numpy as np
src_csv, fgi_csv, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
code = open(__file__).read()
D = pd.read_csv(src_csv, parse_dates=['date']).set_index('date')
d = D.close; asof = d.index[-1].strftime('%Y-%m-%d'); price = float(d.iloc[-1])
meta = [{"label": "make_levels.py", "value": code, "type": "code", "lang": "python"},
        {"label": "Input", "value": "btc-usd-daily.csv (Bitstamp, github.com/rcaljouw/btc-price-history); btc_with_fgi_4h.csv (Fear & Greed from alternative.me via github.com/MetalGrey/btc-fgi-daily-2020)"},
        {"label": "Data up to", "value": asof}]
def dump(name, rows): json.dump({"rows": rows, "meta": meta}, open(f"{outdir}/{name}.json", "w"))
# ---------- key levels ----------
lv = []
ath_i = D.high.idxmax(); lv.append(("All-time high", float(D.high.max()), "Peak on " + ath_i.strftime('%-d %b %Y'), "Peak"))
y = D.loc[d.index[-1] - pd.Timedelta(days=365):]
lv.append(("52-week high", float(y.high.max()), "Highest price in the last year, " + y.high.idxmax().strftime('%b %Y'), "Range"))
lv.append(("52-week low", float(y.low.min()), "Lowest price in the last year, " + y.low.idxmin().strftime('%b %Y'), "Range"))
w = d.resample('W-SUN').last()
lv.append(("200-week average", float(w.rolling(200).mean().iloc[-1]), "Long-run average; has marked most bear-market floors", "Average"))
lv.append(("200-day average", float(d.rolling(200).mean().iloc[-1]), "The main trend line", "Average"))
lv.append(("20-week average", float(w.rolling(20).mean().iloc[-1]), "Medium-term trend line", "Average"))
# volume profile, last 2 years: USD volume in 2.5% log-price bins, using each day's typical price
v2 = D.loc[d.index[-1] - pd.Timedelta(days=730):].copy()
v2['tp'] = (v2.high + v2.low + v2.close) / 3; v2['usd'] = v2.volume * v2.tp
edges = np.exp(np.arange(np.log(v2.low.min()), np.log(v2.high.max()) + 0.025, 0.025))
v2['bin'] = pd.cut(v2.tp, edges)
prof = v2.groupby('bin', observed=True).usd.sum().sort_values(ascending=False)
picked = []
for b in prof.index:
    mid = float(np.sqrt(b.left * b.right))
    if all(abs(np.log(mid / p)) > 0.08 for p in picked): picked.append(mid)
    if len(picked) == 3: break
for i, p in enumerate(sorted(picked)):
    lv.append((f"High-volume zone", p, "One of the 3 busiest trading price zones over the last 2 years (Bitstamp volume)", "Volume"))
rows = []
for name, val, note, kind in lv:
    rows.append({"level": name if name != "High-volume zone" else f"High-volume zone ~${val/1000:.0f}k", "price": round(val), "kind": kind,
                 "dist_pct": round(100 * (val / price - 1), 1), "side": "Above" if val > price else "Below", "note": note})
rows.sort(key=lambda r: -r["price"])
rows.append({"level": "Current price", "price": round(price), "kind": "Now", "dist_pct": 0.0, "side": "Now", "note": "Close on " + asof})
rows.sort(key=lambda r: -r["price"])
dump("levels", rows)
# ---------- Fear & Greed ----------
f = pd.read_csv(fgi_csv, parse_dates=['timestamp'])
f = f.dropna(subset=['Fear & Greed Index']).set_index('timestamp').sort_index()
fd = f['Fear & Greed Index'].astype(float).resample('D').last().dropna()
fd = fd[fd.index <= d.index[-1] + pd.Timedelta(days=1)]
cur = float(fd.iloc[-1]); cur_date = fd.index[-1].strftime('%Y-%m-%d')
def lab(v): return "Extreme fear" if v < 25 else "Fear" if v < 46 else "Neutral" if v < 55 else "Greed" if v < 76 else "Extreme greed"
dump("fgi_now", [{"index": round(cur), "label": lab(cur), "date": cur_date, "avg_30d": round(float(fd.iloc[-30:].mean())), "since": fd.index[0].strftime('%Y-%m-%d')}])
j = pd.DataFrame({"fgi": fd}).join(d.rename('close'), how='inner')
j['fwd12'] = j.close.shift(-84) / j.close - 1   # 12 weeks ahead
wk = j.resample('W-SUN').last()                 # one sample a week to cut overlap
fh = [{"week": (i - pd.Timedelta(days=6)).strftime('%Y-%m-%d'), "fgi": round(float(r.fgi)), "close": round(float(r.close))} for i, r in wk.dropna(subset=['fgi', 'close']).iterrows()]
dump("fgi_history", fh)
ev = wk.dropna(subset=['fwd12']); ev = ev.assign(z=ev.fgi.map(lab))
zr = []
for z in ["Extreme fear", "Fear", "Neutral", "Greed", "Extreme greed"]:
    e = ev[ev.z == z]
    zr.append({"mood": z, "weeks": int(len(e)), "median_12w_pct": round(100 * float(e.fwd12.median()), 1), "up_12w_pct": round(100 * float((e.fwd12 > 0).mean()))})
zr.append({"mood": "All weeks (baseline)", "weeks": int(len(ev)), "median_12w_pct": round(100 * float(ev.fwd12.median()), 1), "up_12w_pct": round(100 * float((ev.fwd12 > 0).mean()))})
dump("fgi_zones", zr)
# split-half robustness check (printed only)
for a, b in (("2020", "2022"), ("2023", "2026")):
    e = ev[a:b]; print(a, b, e.groupby('z').fwd12.agg(['count', 'median']).round(3).to_dict())
print(pd.DataFrame(rows)[["level", "price", "dist_pct"]]); print(cur, lab(cur)); print(pd.DataFrame(zr))
