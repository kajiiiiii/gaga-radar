# -*- coding: utf-8 -*-
"""奈良NEVERLAND（奈良）パーサ。

構造（確認済み・2026-09時点）:
  /schedule/ に今後の公演（WordPress）。各公演:
    <li class="p-schedule-list-item">
      <span class="c-schedule-item-head__date">2026.09.01 Tue</span>  ← 西暦あり
      <h2 class="c-schedule-item-head__title">イベント名</h2>
      <div class="c-schedule-item-act__group">
        <h4 class="c-schedule-item-act__section">- LIVE -</h4>
        <p class="c-schedule-item-act__txt">A / B / C</p></div>
      <div class="c-schedule-item-info"> OPEN/START 17:00/17:30 ADV/DOOR ¥2,500/¥3,000 </div>

日付に西暦があるので推定不要。1ページ表示（今後ぶんを蓄積する運用）。
FOOD/物販などの非ライブ枠は出演者から除外する。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_date, parse_open_start, parse_price, split_artists

_SKIP_SECTION = ("FOOD", "フード", "物販", "DRINK", "ドリンク")


class NeverlandScraper(BaseScraper):

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

        out: list[Appearance] = []
        for item in soup.select(".p-schedule-list-item"):
            date_el = item.select_one(".c-schedule-item-head__date")
            date_s = parse_date(date_el.get_text()) if date_el else None
            if not date_s:
                continue
            title_el = item.select_one(".c-schedule-item-head__title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            parts = []
            for grp in item.select(".c-schedule-item-act__group"):
                sec = grp.select_one(".c-schedule-item-act__section")
                sec_txt = sec.get_text(strip=True) if sec else ""
                if any(s in sec_txt.upper() for s in _SKIP_SECTION):
                    continue
                txt = grp.select_one(".c-schedule-item-act__txt")
                if txt:
                    parts.append(txt.get_text(" ", strip=True))
            lineup = " / ".join(parts)

            open_t = start_t = adv = door = raw = ""
            info = item.select_one(".c-schedule-item-info")
            if info:
                itext = info.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(itext)
                pm = re.search(r"(?:ADV|前売|料金)(.*)$", itext, re.I)
                if pm:
                    adv, door, raw = parse_price(pm.group(1))

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
