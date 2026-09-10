# -*- coding: utf-8 -*-
"""滋賀B-FLAT（滋賀・大津）パーサ。

構造（確認済み・2026-09時点）:
  スケジュール: /?cat=4 （WordPressのカテゴリ一覧）。各公演は表の行:
    <div id="sche_date"><a>2026/09/06(日)</a></div>   ← 西暦あり
    <div id="sche_title"><a>イベント名</a></div>
    （次の行）■OPEN. 17:15 / START. 18:00  ■TICKET: 前売 ¥3,900…  ■ARTIST: climbgrow
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_date, parse_open_start, parse_price, split_artists


class BflatScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/?cat=4")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for td in soup.find_all("td", class_="td_entry"):
            date_el = td.find(id="sche_date")
            date_s = parse_date(date_el.get_text()) if date_el else None
            if not date_s:
                continue
            title_el = td.find(id="sche_title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            open_t = start_t = adv = door = raw = ""
            lineup = ""
            tr = td.find_parent("tr")
            info_tr = tr.find_next_sibling("tr") if tr else None
            if info_tr:
                itext = info_tr.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(itext)
                pm = re.search(r"(?:TICKET|前売|料金)(.*?)(?:■ARTIST|$)", itext, re.I)
                if pm:
                    adv, door, raw = parse_price(pm.group(1))
                am = re.search(r"■?\s*ARTIST\s*[:：]?\s*(.*)$", itext, re.I)
                if am:
                    lineup = am.group(1)

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=f"{self.venue.base_url}/?cat=4",
                ))
        self._cache = out
        return out
