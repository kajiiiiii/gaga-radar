# -*- coding: utf-8 -*-
"""Live House nano（京都）パーサ。

構造（確認済み・2026-09時点）:
  当月=/schedule.php、翌月以降=/schedule_next.php, _next2, _next3, _next4（計 今月+4か月）。
  各公演: <div class="schedule_wrapper schedule"><div class="inner">
            <p class="date">1(火)</p>              ← 日（曜日）
            <p><span class="red">イベント名…</span></p>
            <p class="band">出演者</p>

月ページが「今月から相対」のため、任意の過去月は取得不可。
scrape_month は today からのオフセット(0〜4)に該当する時だけ取得する。
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, split_artists

_FILES = ["schedule.php", "schedule_next.php", "schedule_next2.php",
          "schedule_next3.php", "schedule_next4.php"]


class NanoScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        today = date.today()
        offset = (year * 12 + month) - (today.year * 12 + today.month)
        if not (0 <= offset < len(_FILES)):
            return []  # 取得できるのは今月〜+4か月のみ
        url = f"{self.venue.base_url}/{_FILES[offset]}"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for blk in soup.select(".schedule_wrapper.schedule"):
            date_el = blk.select_one(".date")
            if not date_el:
                continue
            dm = re.search(r"(\d{1,2})", date_el.get_text())
            if not dm:
                continue
            dd = int(dm.group(1))
            if not (1 <= dd <= 31):
                continue
            date_s = f"{year:04d}-{month:02d}-{dd:02d}"

            red = blk.select_one(".red")
            event_name = ""
            if red:
                event_name = red.get_text("\n", strip=True).split("\n")[0]

            band = blk.select_one(".band")
            lineup = band.get_text(" ", strip=True) if band else ""

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name, url=url,
                ))
        return out
