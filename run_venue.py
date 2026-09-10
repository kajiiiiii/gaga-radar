# -*- coding: utf-8 -*-
"""
1会場・1か月だけ取得して確認するツール（動作確認用）。

使い方:
  python run_venue.py varon 2026 10
  python run_venue.py vijon 2026 11

結果を画面に出しつつ output/<venue>_<YYYY>_<MM>.csv に保存する。
まずこれで「出演者がちゃんと分割できているか」を目視確認する。
"""
from __future__ import annotations

import sys

import config
from scrapers import get_scraper
from store.csv_store import write_csv
from venues import VENUES_BY_KEY


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: python run_venue.py <venue_key> <year> <month>")
        print("venue_key 一覧:", ", ".join(VENUES_BY_KEY))
        return 1

    key, year, month = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    venue = VENUES_BY_KEY.get(key)
    if not venue:
        print(f"未知の会場キー: {key}")
        print("一覧:", ", ".join(VENUES_BY_KEY))
        return 1

    print(f"取得: {venue.name} {year}/{month:02d}（詳細取得={config.FETCH_DETAILS}）")
    rows = get_scraper(venue).scrape_month(year, month)

    print(f"\n=== {len(rows)} 行（1出演者1行）===")
    for a in rows:
        print(f"{a.date} | {a.venue} | {a.event_name[:30]} | {a.artist} "
              f"| OPEN {a.open_time} START {a.start_time} | 前売 {a.price_advance} 当日 {a.price_door}")

    out = config.OUTPUT_DIR / f"{key}_{year}_{month:02d}.csv"
    write_csv(rows, out)
    print(f"\n保存: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
