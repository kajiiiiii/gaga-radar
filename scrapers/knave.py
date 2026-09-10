# -*- coding: utf-8 -*-
"""南堀江knave（大阪）パーサ。

構造（確認済み・2026-10で検証）:
  月ページ: /schedule/s_YYYY_MM.html   ← 年月はURLで指定（静的HTML）
  各公演:
    <div class="black-back">
      <h3 id="l_261001">26.10.1<span class="week">THU</span>
          <span class="f-12 white">開場18:00/開演18:30 前￥2,800 当￥3,300(+1D）</span></h3>
    </div>
    <div class="event-details">
      <div class="event-details-left">
        <p>イベント名<br>アーティストA/アーティストB/…</p>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, split_artists


class KnaveScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        yy = year % 100
        url = f"{self.venue.base_url}/schedule/s_{year:04d}_{month:02d}.html"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        out: list[Appearance] = []
        for hdr in soup.select("div.black-back"):
            h3 = hdr.select_one("h3")
            if not h3:
                continue
            htext = h3.get_text(" ", strip=True)

            # 日: "26.10.1" の最後の数字（年月はURL優先）
            dm = re.search(rf"{yy:02d}\.{month}\.(\d{{1,2}})", htext) or re.search(r"\.(\d{1,2})(?:\D|$)", htext)
            if not dm:
                continue
            dd = int(dm.group(1))
            if not (1 <= dd <= 31):
                continue
            date_s = f"{year:04d}-{month:02d}-{dd:02d}"

            open_t = _grab(htext, r"開場\s*(\d{1,2}:\d{2})")
            start_t = _grab(htext, r"開演\s*(\d{1,2}:\d{2})")
            adv = _grab(htext, r"前\s*[￥¥]?\s*([\d,]+)").replace(",", "")
            door = _grab(htext, r"当\s*[￥¥]?\s*([\d,]+)").replace(",", "")
            raw = _grab(htext, r"(開場.*)$")

            details = hdr.find_next_sibling("div", class_="event-details")
            event_name, lineup = "", ""
            if details:
                left = details.select_one(".event-details-left")
                p = left.select_one("p") if left else None
                if p:
                    lines = [x.strip() for x in p.get_text("\n", strip=True).split("\n") if x.strip()]
                    if lines:
                        event_name = lines[0]
                        lineup = " / ".join(lines[1:])

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out


def _grab(text: str, pat: str) -> str:
    m = re.search(pat, text)
    return m.group(1) if m else ""
