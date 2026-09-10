# -*- coding: utf-8 -*-
"""難波Mele（大阪・なんば）パーサ。

構造（確認済み・2026-09で検証）:
  月ページ: /schedule/YYYYMM.html   ← 年月はURLで指定
  各公演:
    <div class="sche_wrap"><div class="sche_box">
      <p class="title">2026年9月3日(木)<br>「イベント名」</p>   ← 日はここ（年月はURL優先）
      <p class="date">OPEN 13:50 START 14:00<br>入場時ドリンク代600円</p>
    </div>
    <p class="text">DJ<br>ORB(Klimt)<br>…</p>   ← 出演者（<br>区切り）
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists

_CATEGORY = {"dj", "live", "act", "guest", "band", "出演"}


class MeleScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schedule/{year:04d}{month:02d}.html"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for wrap in soup.select(".sche_wrap"):
            title_el = wrap.select_one(".title")
            if not title_el:
                continue
            tlines = [x.strip() for x in title_el.get_text("\n", strip=True).split("\n") if x.strip()]
            if not tlines:
                continue
            dm = re.search(r"(\d{1,2})\s*日", tlines[0])
            if not dm:
                continue
            dd = int(dm.group(1))
            if not (1 <= dd <= 31):
                continue
            date_s = f"{year:04d}-{month:02d}-{dd:02d}"
            event_name = tlines[1] if len(tlines) > 1 else tlines[0]

            date_el = wrap.select_one(".date")
            open_t = start_t = adv = door = raw = ""
            if date_el:
                dtext = date_el.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(dtext)
                pm = re.search(r"(?:Charge|チャージ|料金|前売|ADV)(.*)$", dtext, re.I)
                if pm:
                    adv, door, raw = parse_price(pm.group(1))

            text_el = wrap.select_one(".text")
            lineup_lines = []
            if text_el:
                for ln in text_el.get_text("\n", strip=True).split("\n"):
                    ln = ln.strip()
                    if ln and ln.casefold().rstrip(":：") not in _CATEGORY:
                        lineup_lines.append(ln)
            lineup = " / ".join(lineup_lines)

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out
