# -*- coding: utf-8 -*-
"""KYOTO MOJO（京都）パーサ。

WordPress + Modern Events Calendar(MEC) プラグイン。/schedule/ の静的HTMLには
直近〜10件が入っており、各イベントの説明に構造化テキストがある:
  <span class="mec-start-date-label">2026/09/01 (火)</span>
  <h4 class="mec-toggle-title">イベント名</h4>
  <div class="mec-single-event-description">
     [ ACT ] バンドA / バンドB [ Open ] 18:00 [ Start ] 18:30
     [ Ticket ] 前売 ¥5,500 / 当日 ¥6,000 (+1Drink ¥600) …

制約: MECは続きをAJAXで読み込むため、静的HTMLからは直近〜10件のみ取得できる
  （日次で回して蓄積する運用）。全月一括はAJAX対応が必要（TODO）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_date, parse_price, split_artists


class MojoScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/schedule/")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        items = soup.select(".mec-toggle-item")
        descs = soup.select(".mec-single-event-description")
        paired = len(items) == len(descs)

        out: list[Appearance] = []
        for idx, item in enumerate(items):
            label = item.select_one(".mec-start-date-label")
            date_s = parse_date(label.get_text()) if label else None
            if not date_s:
                continue
            title_el = item.select_one(".mec-toggle-title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            lineup = open_t = start_t = adv = door = raw = ""
            desc_text = descs[idx].get_text(" ", strip=True) if paired else ""
            if desc_text:
                lineup = _between(desc_text, r"\[\s*ACT\s*\]", r"\[")
                open_t = _grab(desc_text, r"\[\s*Open\s*\]\s*(\d{1,2}:\d{2})")
                start_t = _grab(desc_text, r"\[\s*Start\s*\]\s*(\d{1,2}:\d{2})")
                tk = _between(desc_text, r"\[\s*Ticket\s*\]", r"(?:詳しく|$)")
                if tk:
                    adv, door, raw = parse_price(tk)

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=f"{self.venue.base_url}/schedule/",
                ))
        self._cache = out
        return out


def _grab(text: str, pat: str) -> str:
    m = re.search(pat, text)
    return m.group(1) if m else ""


def _between(text: str, start: str, end: str) -> str:
    m = re.search(start + r"(.*?)" + end, text)
    return m.group(1).strip() if m else ""
