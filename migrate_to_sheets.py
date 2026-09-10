# -*- coding: utf-8 -*-
"""
ローカルCSV → Google Sheets 初回移行（1回だけ実行）。

いま output/公演DB.csv に溜まっている全データ（履歴含む）をSheetsへアップロードし、
アーティストDBも再集計して書き込む。これを実行すれば、以降はSheetsが本体になり、
ローカルCSVを消してよくなる。

前提: python check_sheets.py が「すべてOK」になっていること。

使い方:
  python migrate_to_sheets.py
"""
from __future__ import annotations

import csv
from datetime import date

import config
import radar
from models import COLUMNS

MASTER_CSV = config.OUTPUT_DIR / "公演DB.csv"


def main() -> int:
    if not config.GOOGLE_CREDENTIALS_FILE.exists():
        print("[error] credentials.json がありません。先に python check_sheets.py で設定を完了してください。")
        return 1
    if not MASTER_CSV.exists():
        print(f"[error] {MASTER_CSV} がありません。先に backfill.py 等で取得してください。")
        return 1

    # CSVを COLUMNS 順の値リストとして読む
    with open(MASTER_CSV, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [[r.get(c, "") for c in COLUMNS] for r in reader]
    print(f"公演DB.csv: {len(rows)} 行を読み込み")

    from store import sheets

    print("公演DB をSheetsへアップロード中…（数十秒〜数分）")
    n = sheets.replace_all_performances(rows)
    print(f"✅ Sheets公演DB: {n} 行を書き込み")

    # アーティストDBを再集計してアップロード
    all_rows = radar.load_appearances(MASTER_CSV)
    summary = radar.build_artist_summary(all_rows, as_of=date.today())
    sheets.replace_artist_summary(radar.ARTIST_HEADER, summary)
    print(f"✅ SheetsアーティストDB: {len(summary)} 名を書き込み")

    print("\n🎉 移行完了。次のステップ:")
    print("  1) スプレッドシートの『公演DB』シートを ファイル>共有>ウェブに公開>CSV で公開しURLを控える")
    print("  2) そのURLを環境変数 RADAR_DATA_URL に設定して streamlit run app.py")
    print("  3) 以降の日次は python daily.py --sheets-only")
    print("  → 動作確認できたら output/ のCSVは削除してOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
