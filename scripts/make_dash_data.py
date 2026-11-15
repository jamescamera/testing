import sys, json, pandas as pd, numpy as np, importlib.util, io, contextlib
src_csv, outdir = sys.argv[1], sys.argv[2]
code = open(__file__).read()
d = pd.read_csv(src_csv, parse_dates=['date']).set_index('date').close
asof = d.index[-1].strftime('%Y-%m-%d')
meta = [{"label": "make_dash_data.py", "value": code, "type": "code", "lang": "python"},
        {"label": "Input", "value": "btc-usd-daily.csv (Bitstamp daily closes via github.com/rcaljouw/btc-price-history)"},
        {"label": "Data up to", "value": asof}]
def dump(name, rows):
    json.dump({"rows": rows, "meta": meta}, open(f"{outdir}/{name}.json", "w"))
w = d.resample('W-SUN').last()
ma200 = d.rolling(200).mean(); ma20w = w.rolling(20).mean()
price = float(d.iloc[-1])
hi50, lo25 = d.rolling(50).max().shift(), d.rolling(25).min().shift()
pos = np.zeros(len(d))
for i in range(1, len(d)):
    pos[i] = 1 if d.iloc[i] > hi50.iloc[i] else (0 if d.iloc[i] < lo25.iloc[i] else pos[i-1])
sig = [
 ("20-week average", "Weekly close above its 20-week average", float(ma20w.iloc[-1])),
 ("200-day average", "Daily close above its 200-day average", float(ma200.iloc[-1])),
 ("Golden cross", "50-day average above 200-day average", float(d.rolling(50).mean().iloc[-1])),
 ("12-month momentum", "Price above where it was a year ago", float(d.iloc[-366])),
 ("50-day breakout", "In after a new 50-day high, out after a 25-day low", float(hi50.iloc[-1]) if pos[-1]==0 else float(lo25.iloc[-1])),
]
rows = []
for name, desc, level in sig:
    if name == "Golden cross":
        inn = bool(d.rolling(50).mean().iloc[-1] > ma200.iloc[-1]); gap = (d.rolling(50).mean().iloc[-1]/ma200.iloc[-1]-1)*100
        lvl = float(ma200.iloc[-1])
    elif name == "50-day breakout":
        inn = bool(pos[-1]==1); lvl = level; gap = (price/lvl-1)*100
    else:
        inn = price > level; lvl = level; gap = (price/lvl-1)*100
    rows.append({"rule": name, "how": desc, "level": round(lvl), "price": round(price), "gap_pct": round(float(gap),1), "state": "IN" if inn else "OUT", "in": 1 if inn else 0, "asof": asof})
dump("signals", rows)
# weekly history since 2014
h = pd.DataFrame({"close": w, "ma20w": ma20w, "ma200d": ma200.resample('W-SUN').last()})['2014-01-01':]
h["in20w"] = (h.close > h.ma20w).astype(int)
hist = [{"week": i.strftime('%Y-%m-%d'), "close": round(float(r.close)), "ma20w": round(float(r.ma20w)), "ma200d": round(float(r.ma200d)), "in20w": int(r.in20w)} for i, r in h.iterrows()]
dump("history", hist)
# backtests
ret = d.pct_change().fillna(0)
S = {"Buy & hold": pd.Series(1, index=d.index),
     "20-week average": (w > ma20w).astype(int).reindex(d.index, method='ffill').fillna(0),
     "200-day average": (d > ma200).astype(int),
     "Golden cross": (d.rolling(50).mean() > ma200).astype(int),
     "12-month momentum": (d > d.shift(365)).astype(int),
     "50-day breakout": pd.Series(pos, index=d.index)}
bt = []
for per, a, b in (("2014–2019", "2014-01-01", "2019-12-31"), ("2020–now", "2020-01-01", None)):
    for k, s in S.items():
        p = s.shift(1).fillna(0); r = (p*ret - p.diff().abs().fillna(0)*0.002)[a:b]
        eq = (1+r).cumprod(); yrs = len(r)/365
        bt.append({"rule": k, "period": per, "return_pa": round(100*(eq.iloc[-1]**(1/yrs)-1)), "worst_drop": round(100*(eq/eq.cummax()-1).min()), "time_in": round(100*p[a:b].mean())})
dump("backtest", bt)
# Strat weekly 2-2-2 bear vs any 2d bar
wk = d.resample('W-SUN').agg(['first']).iloc[:,0]
D = pd.read_csv(src_csv, parse_dates=['date']).set_index('date')
W = D.resample('W-SUN').agg({'high':'max','low':'min','close':'last'}).dropna()
up, dn = W.high > W.high.shift(), W.low < W.low.shift()
t = np.where(up & dn, '3', np.where(up, '2u', np.where(dn, '2d', '1')))
st = []
for name, L in (("Three 2-down weeks in a row (2-2-2 bear)", 3), ("Any 2-down week (comparison)", 1)):
    idx = [i for i in range(L, len(W)-12) if all(t[i-k] == '2d' for k in range(L))]
    nl = np.mean([W.low.iloc[i+1] < W.low.iloc[i] for i in idx])
    l1 = np.mean([W.close.iloc[i+1] < W.close.iloc[i] for i in idx])
    l12 = np.mean([W.close.iloc[i+12] < W.close.iloc[i] for i in idx])
    st.append({"setup": name, "times": len(idx), "next_week_lower_low_pct": round(100*nl), "lower_1w_pct": round(100*l1), "lower_12w_pct": round(100*l12)})
dump("strat", st)
print(json.dumps(rows, indent=0)); print(st); print(len(hist))
