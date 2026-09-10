# -*- coding: utf-8 -*-
"""心斎橋BRONZE（大阪・アメリカ村）パーサ。

構造（確認済み・2026-09で検証）:
  月ページ: /schedulemonth.php?month=YYYYMM   ← 年月はURLで指定
  各公演:
    <div class="eventbox" id="20260902">
      <h4>2026年09月02日(水)</h4>
      <p class="midashi">イベント名</p>
      <p class="bandlist">A / B / C</p>
      <p class="openstart">OPEN 18:00 START 18:30 TICKET adv ¥2500 door ¥3000(別途1D ¥600)</p>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists


class BronzeScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schedulemonth.php?month={year:04d}{month:02d}"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for box in soup.select(".eventbox"):
            dm = re.search(r"(\d{4})(\d{2})(\d{2})", box.get("id", ""))
            if dm:
                date_s = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            else:
                h4 = box.find("h4")
                dd = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", h4.get_text() if h4 else "")
                if not dd:
                    continue
                date_s = f"{int(dd.group(1)):04d}-{int(dd.group(2)):02d}-{int(dd.group(3)):02d}"

            midashi = box.select_one(".midashi")
            event_name = midashi.get_text(" ", strip=True) if midashi else ""

            bandlist = box.select_one(".bandlist")
            lineup = bandlist.get_text(" ", strip=True) if bandlist else ""

            os_el = box.select_one(".openstart")
            open_t = start_t = adv = door = raw = ""
            if os_el:
                ostext = os_el.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(ostext)
                tm = re.search(r"(?:TICKET|adv|ADV)(.*)$", ostext)
                if tm:
                    adv, door, raw = parse_price(tm.group(1))

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out
