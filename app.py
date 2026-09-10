# -*- coding: utf-8 -*-
"""
GAGA Kansai Artist Radar — Webアプリ（Streamlit）

日次で更新される output/公演DB.csv を読み、ブラウザ上で:
  - 発掘レーダー（急拡大アーティストのランキング）
  - アーティスト詳細（出演履歴・出演会場・共演ネットワーク・月別推移）
  - 会場スケジュール
  - 統計
を対話的に見られる。

起動:
  .venv\\Scripts\\streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
import streamlit as st

import config
import radar
from scrapers.base import is_noise_artist, normalize_artist

MASTER = config.OUTPUT_DIR / "公演DB.csv"
# Web上のCSV（Google Sheetsの「ウェブに公開」CSV URL 等）。設定すればPCのCSVは不要。
# 環境変数 RADAR_DATA_URL か、Streamlitのsecrets（RADAR_DATA_URL）で指定する。
def _data_url() -> str:
    url = os.environ.get("RADAR_DATA_URL", "").strip()
    if url:
        return url
    try:
        return str(st.secrets.get("RADAR_DATA_URL", "")).strip()
    except Exception:  # noqa: BLE001  (secrets.toml が無い環境ではここに来る)
        return ""


DATA_URL = _data_url()

st.set_page_config(page_title="GAGA Kansai Artist Radar", page_icon="📡", layout="wide")


# ---------- データ読み込み ----------
def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.fillna("")
    df["dt"] = pd.to_datetime(df["公演日"], errors="coerce")
    df["month"] = df["dt"].dt.strftime("%Y-%m")
    return df


@st.cache_data(ttl=600, show_spinner=False)
def _load_url(url: str) -> pd.DataFrame:
    return _enrich(pd.read_csv(url, dtype=str))


@st.cache_data(show_spinner=False)
def _load_csv(mtime: float) -> pd.DataFrame:
    return _enrich(pd.read_csv(MASTER, dtype=str))


def load_df() -> pd.DataFrame:
    # 優先: Web上のCSV(URL)。無ければローカルCSV。
    if DATA_URL:
        return _load_url(DATA_URL)
    if MASTER.exists():
        return _load_csv(MASTER.stat().st_mtime)
    return pd.DataFrame()


def summary_df(rows: list[dict], as_of: date, window: int) -> pd.DataFrame:
    data = radar.build_artist_summary(rows, as_of=as_of, window=window)
    return pd.DataFrame(data, columns=radar.ARTIST_HEADER)


df = load_df()
if df.empty:
    st.error("データが空です。Web上のCSV(RADAR_DATA_URL)か、ローカルの公演DB.csv を用意してください。"
             "（backfill.py / daily.py で生成）")
    st.stop()

# ---------- ヘッダ ----------
st.title("📡 GAGA Kansai Artist Radar")
st.caption("データ元: " + ("🌐 Web上のCSV(RADAR_DATA_URL)" if DATA_URL else "💻 ローカル 公演DB.csv"))
_min, _max = df["公演日"].replace("", pd.NA).dropna().min(), df["公演日"].replace("", pd.NA).dropna().max()
c1, c2, c3, c4 = st.columns(4)
c1.metric("公演DB 行数", f"{len(df):,}")
c2.metric("ユニーク会場", df["会場"].nunique())
c3.metric("ユニークアーティスト", df[df["出演者"] != ""]["出演者"].map(normalize_artist).nunique())
c4.metric("期間", f"{_min} 〜 {_max}")

tab_radar, tab_artist, tab_venue, tab_stats = st.tabs(
    ["🔭 発掘レーダー", "🎤 アーティスト詳細", "🏠 会場スケジュール", "📊 統計"]
)

# ============================ 発掘レーダー ============================
with tab_radar:
    st.caption("勢い（直近ウィンドウ vs その前）× 活動範囲（会場・エリア）で、"
               "無名からの急拡大を見つける。数字で“観に行く候補”を絞る用途。")
    f1, f2, f3, f4, f5 = st.columns(5)
    as_of = f1.date_input("集計基準日", value=date.today())
    window = f2.slider("ウィンドウ(日)", 30, 180, config.RADAR_WINDOW_DAYS, step=30)
    prefs = sorted(p for p in df["都道府県"].unique() if p)
    sel_pref = f3.multiselect("都道府県", prefs, default=prefs)
    min_apps = f4.slider("最小 直近出演数", 0, 10, 2)
    min_venues = f5.slider("最小 会場数", 1, 6, 1)

    sub = df[df["都道府県"].isin(sel_pref)]
    s = summary_df(sub.to_dict("records"), as_of, window)
    s = s[(s["直近90日"] >= min_apps) & (s["会場数"] >= min_venues)]
    # ウィンドウが90日以外でも列名は「直近90日/前90日」（内部固定表記）
    s = s.sort_values("発掘スコア", ascending=False).reset_index(drop=True)

    st.write(f"該当 **{len(s)}** アーティスト（発掘スコア降順）")
    st.dataframe(s, use_container_width=True, height=520)
    st.download_button("この一覧をCSVで保存", s.to_csv(index=False).encode("utf-8-sig"),
                       file_name="発掘候補.csv", mime="text/csv")

# ============================ アーティスト詳細 ============================
with tab_artist:
    names = sorted({n for n in df["出演者"] if n and not is_noise_artist(n)})
    q = st.text_input("アーティスト名で検索", "")
    cand = [n for n in names if q.lower() in n.lower()] if q else names
    if not cand:
        st.info("該当なし")
    else:
        picked = st.selectbox(f"アーティストを選択（{len(cand)}件）", cand)
        key = normalize_artist(picked)
        mine = df[df["出演者"].map(normalize_artist) == key].sort_values("公演日")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("総出演", len(mine))
        m2.metric("出演会場数", mine["会場"].nunique())
        m3.metric("都道府県数", mine["都道府県"].nunique())
        m4.metric("初→直近", f"{mine['公演日'].min()} 〜 {mine['公演日'].max()}")

        left, right = st.columns([3, 2])
        with left:
            st.subheader("出演履歴")
            st.dataframe(mine[["公演日", "会場", "イベント名", "OPEN", "START"]]
                         .sort_values("公演日", ascending=False),
                         use_container_width=True, height=340)
            st.subheader("月別 出演数")
            mc = mine.groupby("month").size().rename("出演数")
            st.bar_chart(mc)
        with right:
            st.subheader("出演会場")
            st.bar_chart(mine["会場"].value_counts())
            st.subheader("共演ネットワーク（よく共演する相手）")
            co = radar.co_performers(df.to_dict("records"), picked)
            if co:
                st.dataframe(pd.DataFrame(co, columns=["共演者", "共演回数"]).head(25),
                             use_container_width=True, height=260)
            else:
                st.caption("共演データなし")

# ============================ 会場スケジュール ============================
with tab_venue:
    v1, v2 = st.columns(2)
    venue = v1.selectbox("会場", sorted(df["会場"].unique()))
    months = sorted(m for m in df[df["会場"] == venue]["month"].unique() if m)
    month = v2.selectbox("月", months, index=len(months) - 1 if months else 0)
    vm = df[(df["会場"] == venue) & (df["month"] == month)].sort_values("公演日")
    # 1公演1行に畳んで表示（出演者をまとめる）
    grouped = (vm.groupby(["公演日", "イベント名"])
               .agg(出演者=("出演者", lambda s: " / ".join(x for x in s if x)),
                    OPEN=("OPEN", "first"), START=("START", "first"),
                    前売=("前売", "first"), 当日=("当日", "first"))
               .reset_index())
    st.write(f"**{venue} / {month}** … {len(grouped)} 公演")
    st.dataframe(grouped, use_container_width=True, height=520)

# ============================ 統計 ============================
with tab_stats:
    st.subheader("会場別 公演数（出演行ベース）")
    st.bar_chart(df["会場"].value_counts())
    st.subheader("月別 出演数の推移")
    st.line_chart(df.groupby("month").size().rename("出演数"))
    st.subheader("都道府県別 出演数")
    st.bar_chart(df["都道府県"].value_counts())
