# -*- coding: utf-8 -*-
"""心斎橋AtlantiQs（大阪・アメリカ村）パーサ。

構造（確認済み・2026-09時点）:
  /schedule/ に今後の公演。各公演:
    <div class="top_fv_content">
      <h1 class="schedule_title"><div class="txt_date">2026.09.04(Fri)</div>イベント名</h1>
      … <div class="sche_detail"> 出演者：A / B / C  TICKET ADV ¥2,000 / DOOR ¥2,500  TIME OPEN 18:30 / START 19:00 </div>
  日付に西暦あり（推定不要）。1ページ表示（今後分を蓄積）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_date, parse_open_start, parse_price, split_artists


class AtlantiqsScraper(BaseScraper):

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
        for title_el in soup.select(".schedule_title"):
            date_el = title_el.select_one(".txt_date")
            date_s = parse_date(date_el.get_text()) if date_el else None
            if not date_s:
                continue
            # イベント名 = h1テキストから日付部分を除いたもの
            event_name = title_el.get_text(" ", strip=True)
            if date_el:
                event_name = event_name.replace(date_el.get_text(" ", strip=True), "").strip()

            container = title_el.find_parent(class_="top_fv_content") or title_el.parent
            lineup = open_t = start_t = adv = door = raw = ""
            # .sche_detail が3つ（出演者 / 料金 / 時間）。ラベルが無いので内容で判別する。
            for d in (container.select(".sche_detail") if container else []):
                dt = d.get_text("\n", strip=True)
                dt = re.sub(r"^\s*(出演者|TICKET|TIME)\s*[:：]?\s*", "", dt)
                if re.search(r"ADV|DOOR|[¥￥]|前売|当日|料金", dt, re.I):
                    adv, door, raw = parse_price(dt)
                elif re.search(r"OPEN|START|\d{1,2}:\d{2}", dt, re.I):
                    open_t, start_t = parse_open_start(dt)
                elif dt and not lineup:
                    lineup = dt

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


def _between(text: str, start: str, end: str) -> str:
    m = re.search(start + r"(.*?)(?:" + end + r")", text, re.S)
    return m.group(1).strip() if m else ""
