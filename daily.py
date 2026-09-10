# -*- coding: utf-8 -*-
"""
日次更新（毎日実行する想定）。

今日から config.DAILY_MONTHS_AHEAD か月先までを巡回し、
新規の出演だけを公演DBに追記 → アーティストDBを再集計する。

使い方:
  python daily.py            # CSVのみ更新
  python daily.py --sheets   # Google Sheetsも更新

Windowsのタスクスケジューラで毎日AM4:00などに
  <RADER>\.venv\Scripts\python.exe <RADER>\daily.py --sheets
を実行すれば自動化できる。
"""
from __future__ import annotations

import argparse
from datetime import date

import config
import radar
from pipeline import scrape_venues
from store.csv_store import append_dedup
from venues import get_venues

MASTER_CSV = config.OUTPUT_DIR / "公演DB.csv"
ARTIST_CSV = config.OUTPUT_DIR / "アーティストDB.csv"


def _add_months(y: int, m: int, delta: int) -> tuple[int, int]:
    idx = (y * 12 + (m - 1)) + delta
    return idx // 12, idx % 12 + 1


def _write_artist_csv(rows: list[list]) -> None:
    import csv
    with open(ARTIST_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(radar.ARTIST_HEADER)
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", help="カンマ区切りの会場キー")
    ap.add_argument("--verified-only", action="store_true")
    ap.add_argument("--sheets", action="store_true", help="Google Sheetsも更新")
    ap.add_argument("--sheets-only", action="store_true",
                    help="Google Sheetsのみを保存先にする（ローカルCSVを作らない／使わない）。"
                         "データをWebに置いてPCから消したい場合に使う。")
    args = ap.parse_args()
    sheets_only = args.sheets_only
    use_sheets = args.sheets or sheets_only

    keys = args.venues.split(",") if args.venues else None
    venues = get_venues(keys=keys, only_verified=args.verified_only)

    today = date.today()
    start = (today.year, today.month)
    end = _add_months(today.year, today.month, config.DAILY_MONTHS_AHEAD)

    sheets = None
    if use_sheets:
        if not config.GOOGLE_CREDENTIALS_FILE.exists():
            print(f"[warn] {config.GOOGLE_CREDENTIALS_FILE.name} が無いため Sheets を使えません。")
            if sheets_only:
                print("[error] --sheets-only ですが認証情報がありません。READMEの設定後に再実行してください。")
                return 1
        else:
            from store import sheets as sheets  # noqa: PLW0127

    # 既存の公演ID集合（増分取得: 既知公演は詳細ページを再取得しない）
    if sheets_only and sheets:
        known_event_ids = sheets.existing_event_ids()
    else:
        known_event_ids = {r.get("event_id", "") for r in radar.load_appearances(MASTER_CSV)}
    known_event_ids.discard("")

    print(f"日次更新: {start[0]}/{start[1]:02d} 〜 {end[0]}/{end[1]:02d}"
          f"（既知公演 {len(known_event_ids)} 件は詳細再取得スキップ, "
          f"保存先={'Sheetsのみ' if sheets_only else 'CSV'}）")
    rows = scrape_venues(venues, start, end, known_event_ids=known_event_ids)

    # 1) 公演DB 追記（重複除去）
    if not sheets_only:
        added = append_dedup(rows, MASTER_CSV)
        print(f"公演DB(CSV): 新規 {len(added)} 件 → {MASTER_CSV}")

    # 2) 再集計のための全データを取得（Sheetsのみ運用ならSheetsから）
    if sheets_only and sheets:
        n = sheets.append_performances(rows)
        print(f"公演DB(Sheets): 新規 {n} 件")
        all_rows = sheets.load_appearances()
    else:
        all_rows = radar.load_appearances(MASTER_CSV)

    summary = radar.build_artist_summary(all_rows, as_of=today)
    if not sheets_only:
        _write_artist_csv(summary)
        print(f"アーティストDB(CSV): {len(summary)} 名 → {ARTIST_CSV}")
    print("発掘候補 上位10:")
    for row in summary[:10]:
        print(f"  {row[0]} | 出演{row[1]} 会場{row[2]} 直近{row[6]} 増加率{row[8]} スコア{row[-1]}")

    # 3) Sheets 更新（--sheets 時。--sheets-only は上で公演DB追記済み）
    if sheets:
        try:
            if not sheets_only:
                n = sheets.append_performances(rows)
                print(f"Sheets公演DB: 新規 {n} 件")
            sheets.replace_artist_summary(radar.ARTIST_HEADER, summary)
            print(f"SheetsアーティストDB: {len(summary)} 名を書き換え")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] Sheets 更新に失敗: {e}")

    print("完了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
