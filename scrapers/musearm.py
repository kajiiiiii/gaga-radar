# -*- coding: utf-8 -*-
"""MUSE系（arm-live クラシックテンプレート）パーサ。

対象: KYOTO MUSE（確認済み）。ESAKA MUSE も同系クラスだが単一ページで日付が曖昧なため別途。
  月ページ: {base}/liveschedule.html?year=YYYY&month=MM   ← 年月はURLで指定
  各公演:
    <div class="schedule" id="schedule_20260902">
      <div class="live_date"><p class="day">02</p><p class="week">Wed</p></div>
      <dl><dd>
        <h3>イベント名</h3>
        <h4>A / B / C</h4>   ← 出演者（/区切り・リンク）
        <p>OPEN：18:30 / START：19:00<br>ADV.￥2,500 / DOOR￥3,000 1D別￥600</p>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists


class MuseArmScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/liveschedule.html?year={year}&month={month:02d}"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for blk in soup.select(".schedule"):
            bid = blk.get("id", "")
            dm = re.search(r"schedule_(\d{4})(\d{2})(\d{2})", bid)
            if dm:
                date_s = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            else:
                day_el = blk.select_one(".live_date .day")
                dd = re.search(r"(\d{1,2})", day_el.get_text()) if day_el else None
                if not dd:
                    continue
                date_s = f"{year:04d}-{month:02d}-{int(dd.group(1)):02d}"

            h3 = blk.select_one("h3")
            event_name = h3.get_text(" ", strip=True) if h3 else ""
            h4 = blk.select_one("h4")
            lineup = h4.get_text(" ", strip=True) if h4 else ""

            open_t = start_t = adv = door = raw = ""
            p = blk.select_one("dd p") or blk.find("p")
            if p:
                ptext = p.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(ptext)
                pm = re.search(r"(?:ADV|前売|料金)(.*)$", ptext, re.I)
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
