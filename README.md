# GAGA Kansai Artist Radar

関西のライブハウスを毎日巡回し、**「1出演者=1行」** で出演履歴を時系列DB化して、
ブッキング候補（発掘アーティスト）を見つけるための仕組み。

> データで出演者を決めるのではなく、**"観に行くべき候補"をデータで見つける**。
> 最終判断は自分たちの目で、という使い方を想定しています。

---

## いまの状態（重要）

**50会場を登録**（`venues.py`／神戸ART HOUSEは閉店で除外）。うち **32会場が稼働（取得確認済み）**、18会場は個別パーサ待ち（`scraper="todo"`＝パイプラインでは自動スキップ）。未実装の多くは**公式URL・CMS種別を調査済み**（`venues.py`に記載）。
登録状況は `python -c "import venues,json; print(json.dumps(venues.stats(),ensure_ascii=False,indent=2))"` で確認できる。

未実装会場は優先度A→B→Cの順に個別パーサを作っていく（独立系サイトは各社HTMLが違うため1会場ずつ実装が必要。`bassontop.py`/`pangea.py`/`growly.py` が実装の型）。

### 稼働中の10会場

- **ベースオントップ系（共通パーサ1本 `scrapers/bassontop.py` で7会場）**
  心斎橋VARON / 北堀江club vijon / 堺東Goith / 梅田BANGBOO / アメ村BEYOND / 梅田Zeela / アメ村DROP
  → 同グループの会場は `venues.py` に1行足すだけで増やせる。
- **個別パーサ（各サイト専用）**
  - `scrapers/pangea.py` … Pangea（1ページに全公演。出演者/OPEN/START/料金まで取得）
  - `scrapers/varit.py` … 神戸VARIT.（一覧＋詳細ページ。日付・時間を詳細から取得）
  - `scrapers/growly.py` … GROWLY（`?year=&month=` で月指定。表を解析）
  - `scrapers/knave.py` … 南堀江knave（月別静的HTML。出演者/OPEN/START/料金まで）
  - `scrapers/fireloop.py` … 寺田町Fireloop（今後一覧。出演者/OPEN/START/料金まで）
  - `scrapers/socore.py` … SOCORE FACTORY（今後一覧。URLに日付。出演者あり/時間料金なし）
  - `scrapers/hokage.py` … HOKAGE（今後一覧。出演者あり/時間料金なし）
  - `scrapers/nano.py` … Live House nano（今月〜+4か月。出演者あり/時間料金なし）
  - `scrapers/mojo.py` … KYOTO MOJO（MEC。直近〜10件。時間料金あり／出演者の分割は不安定）
  - `scrapers/anima.py` … Live House ANIMA（iCalフィード。2019〜全公演の日付/イベント名／出演者は空）
  - `scrapers/bronze.py` … 心斎橋BRONZE（月別。出演者/OPEN/START/料金まで）
  - `scrapers/mele.py` … 難波Mele（月別。出演者/OPEN/START/料金まで）
  - `scrapers/dewey.py` … 木屋町DEWEY（月別。出演者/OPEN/START/料金まで）
  - `scrapers/neverland.py` … 奈良NEVERLAND（今後一覧。出演者/OPEN/START/料金まで）
  - `scrapers/padoma.py` … 神戸PADOMA（月アーカイブ。出演者/OPEN/START/料金まで）
  - `scrapers/taitora.py` … 神戸 太陽と虎（月見出し＋日で解析。出演者あり/時間料金なし）
  - `scrapers/sinkagura.py` … 新神楽（Jimdo・月別。テキスト解析。出演者/OPEN/START/料金まで）
  - `scrapers/kingsx.py` … KINGSX（Enfoldブログ・記事解析。出演者/OPEN/START/料金まで）
  - `scrapers/muse.py` … OSAKA MUSE（新WPテンプレ）
  - `scrapers/musearm.py` … KYOTO MUSE（arm-live旧テンプレ・月指定）
  - `scrapers/ical.py` … iCal汎用（SUNHALL=Event Organiser / AFTER BEAT=The Events Calendar）
  - `scrapers/janus.py` … Music Club JANUS（今後一覧。出演者/OPEN/START/料金まで）
  - `scrapers/bflat.py` … 滋賀B-FLAT（WP。出演者/OPEN/START/料金まで）
  - `scrapers/clubgate.py` … 和歌山CLUB GATE（My Calendar。公演日/イベント名／出演者は空）

### 会場ごとの注意（データ品質）

- **Pangea/VARIT.** は「今後の公演」を1ページ表示する方式で、ページに西暦が無いため
  **年は日付順から推定**（`infer_years`）。過去の任意月バックフィルには不向きで、
  日次で拾って蓄積していく運用向き。
- **VARIT.** は一覧の出演者情報が薄い公演があり、その場合は出演者空欄で公演だけ残す。
- **GROWLY** はサーバ描画で仕組み上は動くが、**2025〜26年は掲載が無く休止気味**
  （パーサは2024年の実データで検証済み）。掲載が再開すればそのまま取得できる。
- **料金の前売/当日** は文字列からの自動抽出（best-effort）。Pangeaの「学割」やドリンク代
  (¥600)を拾うことがあるため、正確な値が要る時は `料金備考` 列（元文字列）を参照。

---

## セットアップ

Python環境はすでに `.venv/` に作成済み・依存パッケージもインストール済みです。
別PCで一から作る場合:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

以降のコマンドは `.venv` の python で実行します（例）:

```bash
.venv\Scripts\python.exe run_venue.py varon 2026 10
```

---

## 使い方

### 1. 1会場だけ試す（動作確認）

```bash
.venv\Scripts\python.exe run_venue.py varon 2026 10
```

指定会場・指定月を取得して画面表示し、`output/<venue>_<YYYY>_<MM>.csv` に保存します。
**まずここで「出演者がちゃんと1名ずつに分割できているか」を目視確認**してください。
会場キーの一覧は次で確認できます:

```bash
.venv\Scripts\python.exe -c "import venues; [print(v.key, v.name) for v in venues.get_venues()]"
```

### 2. まとめて取得（バックフィル：原則1回だけ）

```bash
# 動作確認済みの会場だけ / config.py の期間
.venv\Scripts\python.exe backfill.py --verified-only

# 会場・期間を指定
.venv\Scripts\python.exe backfill.py --venues varon,vijon --start 2026-01 --end 2026-08

# Google Sheetsにも投入（下の設定が必要）
.venv\Scripts\python.exe backfill.py --verified-only --sheets
```

結果は重複を除いて `output/公演DB.csv` に追記されます。
まずCSVを確認 → 問題なければ `--sheets` を付ける、が安全です。

### 3. 日次更新（毎日実行）

```bash
.venv\Scripts\python.exe daily.py            # CSVのみ
.venv\Scripts\python.exe daily.py --sheets   # Sheetsも更新
```

今日から `DAILY_MONTHS_AHEAD`（既定4）か月先までを巡回し、
**新規の出演だけ**を公演DBに追記 → `output/アーティストDB.csv`（発掘候補）を再集計します。

**増分取得（低負荷化）**: 既に公演DBにある公演は、ベースオントップ系の**詳細ページを再取得しません**
（日次のリクエスト数を大幅に削減）。新規公演のみ詳細（OPEN/START・料金）を取りに行きます。
`credentials.json` が無い状態で `--sheets` を付けても、警告を出してCSV更新は継続します（運用が止まりません）。

#### Windowsタスクスケジューラで自動化（毎日AM4:00）

同梱の **`run_daily.bat`** を使うのが簡単です（作業フォルダ移動・ログ保存まで面倒を見ます）。

「タスクの作成」→ トリガー: 毎日 04:00 → 操作: プログラムの開始
- プログラム/スクリプト: `D:\RADER\run_daily.bat`
- 開始（作業フォルダ）: `D:\RADER`

実行ログは `output\logs\daily_YYYYMMDD_HHMMSS.log` に残ります。
Sheets も更新したい場合は `run_daily.bat` 内のコメント（`--sheets` 付きの行）に切り替えてください。

### 4. 稼働監視（healthcheck）

```bash
.venv\Scripts\python.exe healthcheck.py          # 今月
.venv\Scripts\python.exe healthcheck.py 2026 10  # 指定月
```

各会場の取得件数を一覧表示し、**0件の会場（＝サイト改装等でパーサが壊れた可能性）を警告**します。
サイトは時々HTML構造が変わるので、月1回くらい実行して異常がないか確認するのがおすすめです。
※ 京都GROWLYは現在公演掲載が無く常に0件（休止中）なので、0件でも異常ではありません。

---

## Google Sheets 連携の設定

1. [Google Cloud Console](https://console.cloud.google.com/) で
   **Google Sheets API** と **Google Drive API** を有効化。
2. **サービスアカウント**を作成し、JSONキーをこのフォルダに `credentials.json` として置く。
3. スプレッドシートを作成し、名前を `config.py` の `SPREADSHEET_NAME`
   （既定 `GAGA_Kansai_Artist_Radar`）に合わせる。
4. そのスプレッドシートを、サービスアカウントのメールアドレス
   （`xxx@xxx.iam.gserviceaccount.com`）に **編集者** で共有する。

これで `--sheets` を付けると `公演DB` / `アーティストDB` シートに書き込まれます
（シートが無ければ自動作成）。`credentials.json` は**共有・コミット厳禁**です。

**設定を段階診断するツール**（各段階で実行すると次の一手を教えてくれる）:
```bash
.venv\Scripts\python.exe check_sheets.py
```
**既存のローカルCSV(全履歴)をSheetsへ初回移行**（1回だけ）:
```bash
.venv\Scripts\python.exe migrate_to_sheets.py
```

---

## Webアプリ（ブラウザで見る）

```bash
.venv\Scripts\streamlit run app.py
```

ブラウザで以下が対話的に見られます:
- **🔭 発掘レーダー**: 急拡大アーティストのランキング（都道府県・期間・最小出演数でフィルタ／CSV書き出し）
- **🎤 アーティスト詳細**: 出演履歴・出演会場・**共演ネットワーク**・月別推移
- **🏠 会場スケジュール**: 会場×月の公演一覧
- **📊 統計**: 会場別/月別/都道府県別の件数

既定ではローカルの `output/公演DB.csv` を読みます。**Web上のCSVを読ませる**には
環境変数 `RADAR_DATA_URL`（またはStreamlitのsecrets）に公開CSVのURLを設定します（次項）。

---

## データをWebに置く（このPCからCSVを消せるようにする）

**考え方**: データ本体を **Google Sheets** に置き、CSVはローカルに残さない構成にします。
アプリはSheetsの「ウェブに公開」CSV URLを読み、日次更新もSheetsへ直接行います。

### 手順
1. 上の「Google Sheets 連携の設定」を済ませる（`credentials.json` とシート共有）。
2. 一度データを投入: `python backfill.py --sheets`（または `daily.py --sheets`）。
3. スプレッドシートの `公演DB` シートを **ファイル > 共有 > ウェブに公開 > CSV** で公開し、
   その **CSVのURL** を控える。
4. アプリにそのURLを渡す:
   - ローカルで動かすなら環境変数: `set RADAR_DATA_URL=<公開CSV URL>` してから `streamlit run app.py`
   - Streamlit Community Cloudに載せるなら、アプリのSecretsに `RADAR_DATA_URL="..."` を追加。
5. 以降、日次は **`python daily.py --sheets-only`** で回す（ローカルCSVを作らず、Sheetsだけで
   重複判定・追記・再集計する）。→ **`output/公演DB.csv` / `アーティストDB.csv` は削除してOK**。

### PCを完全に使わない（クラウドで自動運用）
- スクレイパ自体もクラウドで回すなら、同梱の **`.github/workflows/daily.yml`**（GitHub Actions）を使う。
  - GitHubにこのリポジトリを置く。
  - リポジトリ Secrets に `GOOGLE_CREDENTIALS`（サービスアカウントJSONの中身）を登録。
  - 毎日 日本時間4:00 に `daily.py --sheets-only` がクラウド実行され、Sheetsが更新される。
- アプリは **Streamlit Community Cloud** に `app.py` をデプロイし、Secretsに `RADAR_DATA_URL` を設定。
- これで **PCは不要**。ローカルの `output/` や `.venv/` は消して構いません（コードだけ残す）。

> 補足: Google Sheetsは約1,000万セルまで。公演DBは14列なので約70万行まで入り、数年分は問題ありません。
> 上限が近づいたら年ごとにシートを分ける等で対応します。

---

## データ構造

### 公演DB（`output/公演DB.csv` / シート「公演DB」）— 1出演者1行

| 列 | 説明 |
|----|------|
| event_artist_id | 出演者×公演の一意ID（重複防止キー・SHA256） |
| event_id | 公演単位のID（同じ公演の出演者をまとめる用） |
| 公演日 | YYYY-MM-DD |
| 会場 / 都道府県 | |
| イベント名 | |
| 出演者 | **1名**（同じ公演にN組いればN行になる） |
| OPEN / START | 詳細ページから取得 |
| 前売 / 当日 | 料金文字列からの自動抽出（best-effort） |
| 料金備考 | 元の料金文字列（自動抽出の保険） |
| URL / 取得日時 | |

### アーティストDB（`output/アーティストDB.csv` / シート「アーティストDB」）

`daily.py` が公演DB全体から毎回再集計。**発掘スコア降順**。

| 列 | 説明 |
|----|------|
| 出演回数 / 会場数 / 都道府県数 | 活動量・活動範囲 |
| 初出演日 / 直近出演日 | |
| 直近90日 / 前90日 / 増加率 | **勢い（momentum）**。増加率が高い=急拡大 |
| 共演者数 | 共演ネットワークの広さ |
| 主な会場 / 発掘スコア | スコア＝勢い×活動範囲。無名の急拡大を拾う狙い |

`RADAR_WINDOW_DAYS`（既定90）で集計ウィンドウを調整できます。

---

## 会場を増やす

- **ベースオントップ系**（VARON/vijon/Goith と同テンプレート）
  → `venues.py` に1行足すだけ（`scraper="bassontop"`）。
- **独自サイト**（Pangea/VARIT./GROWLY など）
  → `scrapers/<name>.py` の雛形を実装（`scrapers/bassontop.py` の
  `scrape_month` を参考に、公演日/イベント名/出演者/OPEN/START/料金/詳細URL を抽出し、
  `Appearance` を「1出演者1件」で返す）→ `scrapers/__init__.py` の
  `SCRAPER_TYPES` に登録。

### 表記ゆれ・ノイズ対策

- `and more` 等のノイズは `scrapers/base.py` の `_ARTIST_NOISE` で除外済み。
- 「sync sens / sync-sens」のような表記ゆれは `scrapers/base.py` の
  `ARTIST_ALIASES`（別表記→正式名）に追記すると集計時に名寄せされます。

---

## 注意（礼儀・規約）

- 公開スケジュール情報のみを取得します。各サイトの利用規約・`robots.txt` を確認してください。
- リクエスト間隔は `config.py` の `REQUEST_DELAY_SEC`（既定1.2秒）で調整。
  サイトに負荷をかけないよう、間隔を詰めすぎないでください。
- 取得データの利用は自分たちの発掘・ブッキング用途の範囲で。

---

## ファイル構成

```
RADER/
├─ config.py          設定（期間・待機秒数・Sheets名など）
├─ models.py          Appearance（1出演者1行）とID生成
├─ venues.py          会場マスタ（50会場・優先度A/B/C）
├─ pipeline.py        取得の共通処理（増分取得の受け渡し）
├─ radar.py           アーティスト集計・発掘スコア・共演ネットワーク
├─ run_venue.py       1会場1か月テスト
├─ backfill.py        まとめ取得（原則1回。--no-detailsで軽量化）
├─ daily.py           日次更新＋再集計（増分取得）
├─ healthcheck.py     稼働監視（0件会場を警告）
├─ run_daily.bat      タスクスケジューラ用の日次実行バッチ（ログ保存）
├─ scrapers/          会場別パーサ（bassontop/pangea/varit/growly/knave/
│                     socore/hokage/anima/nano/mojo/fireloop/bronze/dewey/
│                     neverland/padoma/mele/taitora/sinkagura/kingsx/muse/
│                     musearm/ical/janus/bflat/clubgate ／ todo=未実装）
├─ store/
│  ├─ csv_store.py    CSV入出力・重複排除
│  └─ sheets.py       Google Sheets連携
└─ output/            CSV出力先（公演DB.csv / アーティストDB.csv / logs/）
```
