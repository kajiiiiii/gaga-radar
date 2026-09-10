# -*- coding: utf-8 -*-
"""live music club PADOMA（兵庫・神戸）パーサ。

構造（確認済み・2026-09で検証）:
  月アーカイブ: /live/archive/YYYY-MM/   ← 年月をURLで指定（WordPress）
  各公演:
    <p class="p-live-info__date">2026.9.01(TUE)</p>   ← 西暦あり
    <h3 class="p-live-info__title">イベント名</h3>
    <... class="p-live-info__act">A / B / C</...>
    <... class="p-live-info__detail">OPEN/START・料金</...>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_date, parse_open_start, parse_price, split_artists


class PadomaScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/live/archive/{year:04d}-{month:02d}/"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for info in soup.select(".p-live-info"):
            date_el = info.select_one(".p-live-info__date")
            date_s = parse_date(date_el.get_text()) if date_el else None
            if not date_s:
                continue
            title_el = info.select_one(".p-live-info__title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            act_el = info.select_one(".p-live-info__act")
            lineup = act_el.get_text(" ", strip=True) if act_el else ""

            open_t = start_t = adv = door = raw = ""
            det = info.select_one(".p-live-info__detail")
            if det:
                dtext = det.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(dtext)
                pm = re.search(r"(?:ADV|前売|料金|TICKET)(.*)$", dtext, re.I)
                if pm:
                    adv, door, raw = parse_price(pm.group(1))

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out
