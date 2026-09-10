# -*- coding: utf-8 -*-
"""
スクレイパ共通基盤。

- HTTP取得（リトライ・待機・UA付き）
- 月の反復ユーティリティ
- 料金 / OPEN・START の文字列パーサ
- BaseScraper: 会場ごとのパーサはこれを継承して scrape_month() だけ書く
"""
from __future__ import annotations

import re
import time
from datetime import date
from typing import Iterator

import requests

import config
from models import Appearance
from venues import Venue

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": config.USER_AGENT})
    return _session


def fetch(url: str) -> str | None:
    """URLを取得して本文(str)を返す。失敗時は None。礼儀として毎回待機する。"""
    last_err = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = _get_session().get(url, timeout=config.REQUEST_TIMEOUT_SEC)
            time.sleep(config.REQUEST_DELAY_SEC)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            # 文字コードは概ねUTF-8。稀にShift_JISのサイトはapparent_encodingで補正。
            if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                resp.encoding = resp.apparent_encoding
            return resp.text
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(config.REQUEST_DELAY_SEC * attempt)
    print(f"    [warn] fetch failed: {url} ({last_err})")
    return None


def iter_months(start: tuple[int, int], end: tuple[int, int]) -> Iterator[tuple[int, int]]:
    y, m = start
    ey, em = end
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


# ---- パーサ・ユーティリティ ----------------------------------------------

_YEN_RE = re.compile(r"[¥￥\\]?\s*([0-9][0-9,]{2,})")
_DATE_RE = re.compile(r"(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})")


def parse_date(text: str) -> str | None:
    """'2026.10.03(Sat)' や '2026年10月3日' → '2026-10-03'。"""
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"


# 出演者名ではない“ノイズ”。完全一致で除外する。
_ARTIST_NOISE = {
    "and more", "and more...", "...and more", "and more!!", "and more!",
    "more", "その他", "他", "他多数", "ほか", "etc", "etc.", "画像参照",
    "出演者", "act", "…", "...", "。", "ゲスト", "and more.",
}


def split_artists(text: str) -> list[str]:
    """出演者文字列を1名ずつに分割。区切りは / ／ ，、 改行 に対応。

    末尾の 'and more' 等のノイズは除外する。表記ゆれ（全角/半角スペース等）は
    normalize_artist() で吸収する。
    """
    if not text:
        return []
    parts = re.split(r"[/／,、\n\r]+", text)
    seen, out = set(), []
    for p in parts:
        name = p.strip().strip("・").strip()
        if not name:
            continue
        if name.casefold() in _ARTIST_NOISE:
            continue
        key = normalize_artist(name)
        if key and key not in seen:
            seen.add(key)
            out.append(name)
    return out


# 表記ゆれ吸収用のエイリアス表（必要に応じて追記）。
# 左（別表記）→ 右（正式名）。集計時の名寄せに使う。
ARTIST_ALIASES: dict[str, str] = {
    # 例: "sync sens": "sync-sens",
}


def is_noise_artist(name: str) -> bool:
    """出演者名として無効（'and more' 等のノイズ）なら True。"""
    n = (name or "").strip().strip("・").strip()
    return (not n) or (n.casefold() in _ARTIST_NOISE)


def normalize_artist(name: str) -> str:
    """名寄せ用の正規化キー。全角/半角スペースやハイフンの揺れを吸収。"""
    n = (name or "").strip()
    n = ARTIST_ALIASES.get(n, n)
    n = n.replace("　", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n.casefold()


def infer_years(months: list[int], today: date | None = None) -> list[int]:
    """月だけ分かる“今後の公演リスト”に西暦を割り当てる。

    リストは日付順（今後）である前提。月が前より小さくなったら年をまたいだと判断。
    例: today=2026-11, months=[11,12,1,2] → [2026,2026,2027,2027]
    """
    today = today or date.today()
    years: list[int] = []
    year = today.year
    prev: int | None = None
    for mm in months:
        if prev is None:
            year = today.year + 1 if mm < today.month else today.year
        elif mm < prev:
            year += 1
        years.append(year)
        prev = mm
    return years


def parse_open_start(text: str) -> tuple[str, str]:
    """'17:30/18:30' や 'OPEN 17:30 START 18:30' → ('17:30','18:30')。"""
    times = re.findall(r"(\d{1,2}:\d{2})", text or "")
    if len(times) >= 2:
        return times[0], times[1]
    if len(times) == 1:
        return times[0], ""
    return "", ""


def parse_price(text: str) -> tuple[str, str, str]:
    """料金文字列 → (前売, 当日, 元文字列)。ざっくり2つの金額を拾う best-effort。"""
    raw = (text or "").strip()
    if not raw:
        return "", "", ""
    nums = [n.replace(",", "") for n in _YEN_RE.findall(raw)]
    nums = [n for n in nums if int(n) >= 500]  # 1D等の小さい数字を除外
    adv = nums[0] if len(nums) >= 1 else ""
    door = nums[1] if len(nums) >= 2 else ""
    return adv, door, raw


# ---- 基底クラス -----------------------------------------------------------

class BaseScraper:
    """会場パーサの基底。サブクラスは scrape_month() を実装する。"""

    def __init__(self, venue: Venue):
        self.venue = venue
        # 既にDBにある公演ID集合。日次の増分取得で「詳細ページの再取得」を省くのに使う。
        # 空なら全件フェッチ（バックフィル時の挙動）。
        self.known_event_ids: set[str] = set()

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        raise NotImplementedError

    def scrape_range(self, start: tuple[int, int], end: tuple[int, int]) -> list[Appearance]:
        out: list[Appearance] = []
        for y, m in iter_months(start, end):
            try:
                rows = self.scrape_month(y, m)
                print(f"  {self.venue.name} {y}/{m:02d}: {len(rows)} 出演")
                out.extend(rows)
            except Exception as e:  # noqa: BLE001
                print(f"  [error] {self.venue.name} {y}/{m:02d}: {e}")
        return out
