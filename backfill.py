# -*- coding: utf-8 -*-
"""
過去〜先の数か月をまとめて取得する（原則1回だけ実行）。

使い方:
  python backfill.py                       # 全会場 / config の期間
  python backfill.py --verified-only       # 構造確認済みの会場だけ
  python backfill.py --venues varon,vijon  # 会場を指定
  python backfill.py --start 2026-01 --end 2026-08
  python backfill.py --sheets              # Google Sheetsにも投入

出力は常に output/公演DB.csv（重複排除して追記）。まずCSVを目視確認してから
--sheets を付けるのが安全。
"""
from __future__ import annotations

import argparse

import config
from pipeline import scrape_venues
from store.csv_store import append_dedup
from venues import get_venues

MASTER_CSV = config.OUTPUT_DIR / "公演DB.csv"


def _ym(s: str) -> tuple[int, int]:
    y, m = s.split("-")
    return int(y), int(m)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", help="カンマ区切りの会場キー")
    ap.add_argument("--verified-only", action="store_true", help="構造確認済みの会場だけ")
    ap.add_argument("--start", help="開始月 YYYY-MM")
    ap.add_argument("--end", help="終了月 YYYY-MM")
    ap.add_argument("--sheets", action="store_true", help="Google Sheetsにも投入")
    ap.add_argument("--no-details", action="store_true",
                    help="詳細ページを取得しない（OPEN/START/料金は空だが高速・低負荷）")
    args = ap.parse_args()

    if args.no_details:
        config.FETCH_DETAILS = False  # スクレイパは実行時にこの値を参照する

    keys = args.venues.split(",") if args.venues else None
    venues = get_venues(keys=keys, only_verified=args.verified_only)
    if not venues:
        print("対象会場がありません。")
        return 1

    start = _ym(args.start) if args.start else config.BACKFILL_START
    end = _ym(args.end) if args.end else config.BACKFILL_END

    print(f"対象会場: {', '.join(v.name for v in venues)}")
    rows = scrape_venues(venues, start, end)

    added = append_dedup(rows, MASTER_CSV)
    print(f"CSV追記: {len(added)} 件（新規） → {MASTER_CSV}")

    if args.sheets:
        from store import sheets
        n = sheets.append_performances(rows)
        print(f"Sheets追記: {n} 件（新規） → {config.SPREADSHEET_NAME} / {config.WORKSHEET_PERFORMANCES}")

    print("完了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
