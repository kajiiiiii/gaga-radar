# -*- coding: utf-8 -*-
"""KINGSX（兵庫・神戸三宮）パーサ。

Enfold(ブログ型)テーマ。/kings-x-schedule/ に公演が記事(article)として並ぶ。
各記事のテキスト:
    2026.09.07 mon          ← 公演日（記事タイトル先頭）
    2026年7月10日 … 作成者: kingsx   ← 投稿メタ（無視）
    "LIB"                    ← イベント名（OPEN/STARTの直前行）
    OPEN/START 17:00/17:30
    adv ¥2,000 / door ¥2,500
    出演                      ← 以降が出演者（1行1組）
    SkaPunCelt
    Astel Glow
    …

投稿日ではなく記事先頭の「YYYY.MM.DD」を公演日として使う。ブログ表示のため
直近ぶんが中心（日次で拾って蓄積する運用）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists

_EVENT_DATE = re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})")
_META = re.compile(r"カテゴリ|作成者|kingsx|KINGS\s*X|スケジュール|^/$|^\d{4}[.\-年]|^\d+$")


class KingsxScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/kings-x-schedule/")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for art in soup.select("article"):
            lines = [ln.strip() for ln in art.get_text("\n").split("\n") if ln.strip()]
            if not lines:
                continue
            dm = _EVENT_DATE.search(lines[0]) or _EVENT_DATE.search("\n".join(lines[:3]))
            if not dm:
                continue
            date_s = f"{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"

            os_idx = next((i for i, l in enumerate(lines) if re.search(r"OPEN", l, re.I)), None)
            open_t = start_t = ""
            if os_idx is not None:
                open_t, start_t = parse_open_start(lines[os_idx])

            price_line = next((l for l in lines if re.search(r"adv|door|¥|￥|前売|当日", l, re.I)), "")
            adv, door, raw = parse_price(price_line) if price_line else ("", "", "")

            event_name = ""
            if os_idx is not None:
                for j in range(os_idx - 1, -1, -1):
                    if lines[j] and not _META.search(lines[j]):
                        event_name = lines[j]
                        break

            artists: list[str] = []
            act_idx = next((i for i, l in enumerate(lines) if re.match(r"出演|LIVE|ACT", l, re.I)), None)
            if act_idx is not None:
                for l in lines[act_idx + 1:]:
                    if l.startswith("http") or _META.search(l) or re.search(r"\d{4}-\d{2}-\d{2}", l):
                        break
                    artists.extend(split_artists(l))

            for name in (artists or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=f"{self.venue.base_url}/kings-x-schedule/",
                ))
        self._cache = out
        return out
