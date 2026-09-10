# -*- coding: utf-8 -*-
"""和歌山CLUB GATE（和歌山）パーサ。

WordPress + My Calendar プラグイン。/schdule/ がカレンダー表示:
  <td id="calendar-2026-09-06" class="... has-events ...">
     <h3 class="event-title summary"><a href="...?mc_id=2047">N/A: イベント名</a></h3>

日付はセルidから確定。出演者はグリッドに無い（詳細ページ側）ため、ここでは
公演日・イベント名まで取得する（出演者は空）。月は My Calendar の ?yr=&month= で指定。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch


class ClubgateScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schdule/?yr={year}&month={month}"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for cell in soup.select("td[id^=calendar-]"):
            dm = re.search(r"calendar-(\d{4})-(\d{2})-(\d{2})", cell.get("id", ""))
            if not dm:
                continue
            if (int(dm.group(1)), int(dm.group(2))) != (year, month):
                continue
            date_s = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            for title_el in cell.select(".event-title a, .event-title"):
                name = re.sub(r"^N/A\s*[:：]\s*", "", title_el.get_text(" ", strip=True))
                if not name:
                    continue
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=name, artist="", url=url,
                ))
                break  # .event-title a と .event-title の重複を避ける
        return out
