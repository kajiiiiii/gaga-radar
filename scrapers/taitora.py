# -*- coding: utf-8 -*-
"""music zoo KOBE 太陽と虎（兵庫・神戸）パーサ。

構造（確認済み・2026-09時点）:
  /live に今後の公演（WordPress）。月見出し「YYYY年MM月」のあとに、その月の公演が
  日付(日)のみで並ぶ:
    YYYY年MM月
    <li id="date-xxxx"><a href="...">
      <div class="live-date"><p>01<span class="weekday">(火)</span></p></div>
      <div class="live-artist-box">
        <p class="live-title">イベント名</p>
        <h3>ヘッドライナー</h3>
        <p class="live-artist">A / B / C<br>DJ:…</p>

年・月は直近の「YYYY年MM月」見出しから決め、日は各公演から取る。
1ページ表示（今後ぶんを蓄積する運用）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, split_artists

_TOKEN = re.compile(r'(?P<hdr>(\d{4})\s*年\s*(\d{1,2})\s*月)|(?P<li><li[^>]*id="date-\d+".*?</li>)', re.S)


class TaitoraScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/live")
        if not html:
            self._cache = []
            return self._cache

        out: list[Appearance] = []
        cur_year = cur_month = None
        for m in _TOKEN.finditer(html):
            if m.group("hdr"):
                cur_year, cur_month = int(m.group(2)), int(m.group(3))
                continue
            if cur_year is None:
                continue
            out.extend(self._parse_li(m.group("li"), cur_year, cur_month))
        self._cache = out
        return out

    def _parse_li(self, li_html: str, year: int, month: int) -> list[Appearance]:
        li = BeautifulSoup(li_html, "lxml")
        date_el = li.select_one(".live-date")
        dm = re.search(r"(\d{1,2})", date_el.get_text()) if date_el else None
        if not dm:
            return []
        dd = int(dm.group(1))
        if not (1 <= dd <= 31):
            return []
        date_s = f"{year:04d}-{month:02d}-{dd:02d}"

        title_el = li.select_one(".live-title")
        event_name = title_el.get_text(" ", strip=True) if title_el else ""
        head = li.select_one(".live-artist-box h3")
        artist_el = li.select_one(".live-artist")
        parts = []
        if head:
            parts.append(head.get_text(" ", strip=True))
        if artist_el:
            parts.append(artist_el.get_text("\n", strip=True))
        lineup = "\n".join(parts)

        a = li.select_one("a")
        url = a["href"] if (a and a.has_attr("href")) else f"{self.venue.base_url}/live"

        rows = []
        for name in (split_artists(lineup) or [""]):
            rows.append(Appearance(
                date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                event_name=event_name, artist=name, url=url,
            ))
        return rows
