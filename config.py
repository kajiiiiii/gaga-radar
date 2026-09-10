# -*- coding: utf-8 -*-
"""
GAGA Kansai Artist Radar - 設定ファイル

ここを書き換えるだけで挙動を調整できます。
"""
from pathlib import Path

# ---- パス ----
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---- スクレイピングの礼儀 ----
# サイトへの負荷を避けるため、リクエスト間に必ず待機を入れます。
USER_AGENT = "gaga-radar/1.0 (+contact: kajiiiiii0712@gmail.com)"
REQUEST_DELAY_SEC = 1.2      # 1リクエストごとの待機秒数
REQUEST_TIMEOUT_SEC = 25
MAX_RETRIES = 3

# 公演詳細ページまで取得して OPEN/START・料金を埋めるか。
# True にすると精度は上がるがリクエスト数が増える（＝遅くなる）。
FETCH_DETAILS = True

# ---- バックフィル対象期間 ----
# (year, month) から (year, month) まで（両端含む）。
# 例: 2026年1月〜8月 → START=(2026,1), END=(2026,8)
BACKFILL_START = (2026, 1)
BACKFILL_END = (2026, 12)

# ---- 日次更新 ----
# 今日から何か月先まで確認するか。
DAILY_MONTHS_AHEAD = 4

# ---- Google Sheets ----
# サービスアカウントの JSON キー。Google Cloud Console で発行し、ここに置く。
GOOGLE_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
SPREADSHEET_NAME = "GAGA_Kansai_Artist_Radar"
WORKSHEET_PERFORMANCES = "公演DB"        # 1出演者1行の生データ
WORKSHEET_ARTISTS = "アーティストDB"      # 集計結果（daily.py が再計算）

# 発掘候補判定に使う集計ウィンドウ（日数）
RADAR_WINDOW_DAYS = 90
