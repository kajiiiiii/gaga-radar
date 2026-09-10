# -*- coding: utf-8 -*-
"""MUSE系（OSAKA MUSE / ESAKA MUSE / KYOTO MUSE）パーサ。

MUSEチェーン共通テンプレート（WordPress）。確認済み: OSAKA MUSE
  http://osaka.muse-live.com/schedule/
  各公演:
    <article class="media schedule">
      <div class="event_date"><p class="value-of-int"><span class="month">9</span>.01</p>
        <p class="value-is-2">TUE</p></div>
      <h4 class="media-heading entry-title">イベント名</h4>
      <div class="schedule_content">A / B / C … TIME OPEN… </div>
      <div class="schedule_info_list">TIME OPEN 19:00 / START 19:30 PRICE ADV.¥2,400 / DOOR.¥3,000 …</div>

月/日はあるが西暦が無いので日付順から推定（infer_years）。1ページ表示。
base_url を変えれば ESAKA/KYOTO にも流用可（稼働URL確定後に venues.py で有効化）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, infer_years, parse_open_start, parse_price, split_artists


class MuseScraper(BaseScraper):

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

        raw: list[dict] = []
        months: list[int] = []
        for art in soup.select(".media.schedule"):
            date_el = art.select_one(".event_date")
            md = re.search(r"(\d{1,2})\s*\.\s*(\d{1,2})", date_el.get_text(" ", strip=True)) if date_el else None
            if not md:
                continue
            mm, dd = int(md.group(1)), int(md.group(2))

            title_el = art.select_one(".entry-title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            content = art.select_one(".schedule_content")
            lineup = ""
            if content:
                ctext = content.get_text(" ", strip=True)
                lineup = re.split(r"TIME|OPEN", ctext)[0]

            open_t = start_t = adv = door = raw_p = ""
            info = art.select_one(".schedule_info_list")
            if info:
                itext = info.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(itext)
                pm = re.search(r"(?:PRICE|ADV|前売|料金)(.*)$", itext, re.I)
                if pm:
                    adv, door, raw_p = parse_price(pm.group(1))

            raw.append(dict(mm=mm, dd=dd, name=event_name, lineup=lineup,
                            open_t=open_t, start_t=start_t, adv=adv, door=door, raw=raw_p))
            months.append(mm)

        years = infer_years(months)

        out: list[Appearance] = []
        for e, y in zip(raw, years):
            date_s = f"{y:04d}-{e['mm']:02d}-{e['dd']:02d}"
            for name in (split_artists(e["lineup"]) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=e["name"], artist=name,
                    open_time=e["open_t"], start_time=e["start_t"],
                    price_advance=e["adv"], price_door=e["door"], price_raw=e["raw"],
                    url=f"{self.venue.base_url}/schedule/",
                ))
        self._cache = out
        return out
