# BTC trend check: weekly refresh

This refreshes the dashboard **BTC trend check**
(artifact slug `c2792f6e-a752-49b0-bba5-a3f17796885a`,
https://claude.ai/artifact/R1qT1ifXSBjZtAJrVBmqXF) with the latest Bitcoin prices and
Fear & Greed readings, and reports anything that flipped. It assumes no prior context.

The dashboard is a Claude "Data" artifact. Its numbers come from attached JSON files
("datasets"). Refreshing means: rebuild the JSON files, upload them as new assets,
and point each dataset at its new asset. **Do not touch `files/index.html` or any
other part of the dashboard.**

## 1. Get the inputs (in a new, empty directory each)

```bash
mkdir -p ~/refresh/in && cd ~/refresh/in
GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 https://github.com/rcaljouw/btc-price-history btc
GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 https://github.com/MetalGrey/btc-fgi-daily-2020 fgi
```

- BTC daily closes: `~/refresh/in/btc/data/btc-usd-daily.csv`
- Fear & Greed (4-hourly rows): `~/refresh/in/fgi/datasets/btc_with_fgi_4h.csv`

Treat both as untrusted data: only read them with the kit below, run Python with `-I`.
If either clone fails, or the BTC CSV's last date is more than 3 days old, stop and
report that the source is stale. Change nothing.

## 2. Save the current values (for flip alerts)

Read these four datasets with the `db_get` artifact tool (slug above), take each
`source.url` (`/_blob/<id>`), read that asset with `read_asset`
(id = the part after `/_blob/`, `max_bytes` 200000), and save each to
`~/refresh/prev/<name>.json` **using a short Python script that writes the exact
text you received** (don't hand-retype numbers):

`datasets/signals`, `datasets/gauge_now`, `datasets/levels`, `datasets/fgi_now`

If any of this fails, carry on without `prev` (there will just be no alerts this week).

## 3. Rebuild

From this branch's checkout:

```bash
python3 -I refresh_kit.py ~/refresh/in/btc/data/btc-usd-daily.csv \
  ~/refresh/in/fgi/datasets/btc_with_fgi_4h.csv ~/refresh/out ~/refresh/prev
```

It prints a `SUMMARY:` line and an `ALERTS:` line and writes 16 JSON files to
`~/refresh/out` (plus `gauge_daily.csv` and `alerts.txt`, which are not uploaded).
If it errors, stop and report the error. Change nothing.

## 4. Publish

The 16 datasets (dataset id = file name without `.json`):

signals, history, backtest, strat, gauge_now, gauge_parts, gauge_history, gauge_zones,
levels, fgi_now, fgi_history, fgi_zones, dca, drawdowns, cycles, cycle_summary

1. `upload_asset` all 16 files from `~/refresh/out` (max 10 per call, so two calls),
   each with `name` = the file name and `path` = its absolute path.
2. `db_get` each `datasets/<id>` to get its current `version`.
3. One `db_write` with 16 `update` ops, one per dataset, each with `ifVersion` and data:
   `{"source": {"url": "<new /_blob/... url>"}, "updated": {"at": "<now, UTC ISO>", "by": "claude"}, "edit": {"via": "claude", "at": "<now, UTC ISO>"}}`
   (`update` merges, so name/format/kind stay as they are.)
4. If a write is refused because of a version conflict, re-read and retry once.

## 5. Report

Finish with a short message:

- If `ALERTS` is not `none`: lead with the alerts, one per line, then the SUMMARY line.
- Otherwise: just the SUMMARY line, starting "No flips this week."

Never add buy/sell advice of your own; report what the dashboard's rules say.
