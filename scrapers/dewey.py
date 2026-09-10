# -*- coding: utf-8 -*-
"""木屋町DEWEY（京都）パーサ。

構造（確認済み・2026-09で検証）:
  月ページ: /schedule/YYYY/MM/index.html   ← 年月はURLで指定
  各公演は表の行:
    <div class="date"> 4 <br>(fri)</div>
    <div class="eventTitle">イベント名</div>
    <div class="actor">A／B／C</div>
    <div class="openstart">open19:00 start19:30</div>
    <div class="charge">￥2,500(+1DRINK￥600)／配信￥2,000</div>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists


class DeweyScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schedule/{year:04d}/{month:02d}/index.html"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for date_el in soup.select(".date"):
            dm = re.search(r"(\d{1,2})", date_el.get_text())
            if not dm:
                continue
            dd = int(dm.group(1))
            if not (1 <= dd <= 31):
                continue
            row = date_el.find_parent("tr") or date_el.parent
            date_s = f"{year:04d}-{month:02d}-{dd:02d}"

            title_el = row.select_one(".eventTitle")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            actor_el = row.select_one(".actor")
            lineup = actor_el.get_text(" ", strip=True) if actor_el else ""

            os_el = row.select_one(".openstart")
            open_t, start_t = parse_open_start(os_el.get_text(" ", strip=True)) if os_el else ("", "")

            charge_el = row.select_one(".charge")
            adv = door = raw = ""
            if charge_el:
                adv, door, raw = parse_price(charge_el.get_text(" ", strip=True))

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out
