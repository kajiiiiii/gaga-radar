# -*- coding: utf-8 -*-
"""Google Sheets 連携。

事前準備:
  1) Google Cloud Console で Google Sheets API と Google Drive API を有効化。
  2) サービスアカウントを作成し、JSONキーを credentials.json としてこのフォルダに置く。
  3) 対象スプレッドシート(config.SPREADSHEET_NAME)を、
     そのサービスアカウントのメールアドレスに「編集者」で共有する。

gspread は遅延importしているので、CSVだけ使う分にはインストール不要。
"""
from __future__ import annotations

import config
from models import COLUMNS, Appearance
from store.csv_store import dedup


def _client():
    import gspread  # 遅延import
    return gspread.service_account(filename=str(config.GOOGLE_CREDENTIALS_FILE))


def _open_worksheet(title: str, header: list[str]):
    gc = _client()
    try:
        sh = gc.open(config.SPREADSHEET_NAME)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"スプレッドシート '{config.SPREADSHEET_NAME}' を開けません。"
            f"サービスアカウントに共有済みか確認してください。({e})"
        )
    try:
        ws = sh.worksheet(title)
    except Exception:  # noqa: BLE001
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(len(header), 12))
        ws.append_row(header, value_input_option="RAW")
    # ヘッダーが空なら入れる
    first = ws.row_values(1)
    if not first:
        ws.append_row(header, value_input_option="RAW")
    return ws


def existing_ids() -> set[str]:
    """公演DBの1列目(event_artist_id)から既存IDを読む。"""
    ws = _open_worksheet(config.WORKSHEET_PERFORMANCES, COLUMNS)
    col = ws.col_values(1)  # ヘッダー含む
    return set(col[1:]) if len(col) > 1 else set()


def existing_event_ids() -> set[str]:
    """公演DBの2列目(event_id)から既存の公演IDを読む（増分取得の詳細スキップ用）。"""
    ws = _open_worksheet(config.WORKSHEET_PERFORMANCES, COLUMNS)
    col = ws.col_values(2)
    return set(col[1:]) if len(col) > 1 else set()


def load_appearances() -> list[dict]:
    """公演DB全体を dict のリストで読む（アプリ/集計がSheetsを直接使う場合）。

    gspreadは数字っぽいセルをint/float化するため、CSV読込(全部str)と挙動を合わせて
    すべて文字列に統一する（下流の集計は値がstr前提）。
    """
    ws = _open_worksheet(config.WORKSHEET_PERFORMANCES, COLUMNS)
    records = ws.get_all_records()  # ヘッダーをキーにした dict のリスト
    return [{k: ("" if v is None else str(v)) for k, v in r.items()} for r in records]


def append_performances(appearances: list[Appearance]) -> int:
    """新規の出演行だけ公演DBに追記。追加件数を返す。"""
    appearances = dedup(appearances)
    have = existing_ids()
    rows = [a.to_row() for a in appearances if a.event_artist_id not in have]
    if not rows:
        return 0
    ws = _open_worksheet(config.WORKSHEET_PERFORMANCES, COLUMNS)
    # まとめて追記（API呼び出し回数を抑える）
    ws.append_rows(rows, value_input_option="RAW")
    return len(rows)


def replace_artist_summary(header: list[str], rows: list[list]) -> None:
    """アーティストDBを丸ごと置き換える（毎回再集計する想定）。"""
    ws = _open_worksheet(config.WORKSHEET_ARTISTS, header)
    ws.clear()
    ws.update([header] + rows, value_input_option="RAW")


def replace_all_performances(rows: list[list], chunk: int = 5000) -> int:
    """公演DBを丸ごと置き換える（ローカルCSV→Sheetsの初回移行用）。

    rows は models.COLUMNS の順に並んだ値の2次元リスト（ヘッダー除く）。
    大量行はチャンクに分けて追記する（APIの上限対策）。
    """
    ws = _open_worksheet(config.WORKSHEET_PERFORMANCES, COLUMNS)
    ws.clear()
    ws.update([COLUMNS], value_input_option="RAW")  # ヘッダー
    for i in range(0, len(rows), chunk):
        ws.append_rows(rows[i:i + chunk], value_input_option="RAW")
        print(f"  Sheets公演DB: {min(i + chunk, len(rows))}/{len(rows)} 行アップロード")
    return len(rows)
