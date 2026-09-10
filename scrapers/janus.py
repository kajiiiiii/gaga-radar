# -*- coding: utf-8 -*-
"""Music Club JANUS（大阪・東心斎橋）パーサ。

構造（確認済み・2026-09時点）:
  /schedule に今後の公演（WordPress）。各公演:
    <div class="c-scheduleList__inner">
      <div class="c-scheduleList__date--month">09/</div>
      <div class="c-scheduleList__date--date">01</div>   ← 月/日（年なし→推定）
      <div class="c-scheduleList__about">
         イベント名
         A / B / C                ← 出演者
         OPEN/START  18:00 / 18:30
         ADV/DOOR  ￥2,800 / ￥3,300
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, infer_years, parse_open_start, parse_price, split_artists


class JanusScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/schedule")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        raw: list[dict] = []
        months: list[int] = []
        for inner in soup.select(".c-scheduleList__inner"):
            mon_el = inner.select_one(".c-scheduleList__date--month")
            day_el = inner.select_one(".c-scheduleList__date--date")
            if not (mon_el and day_el):
                continue
            mm = int(re.sub(r"\D", "", mon_el.get_text()) or 0)
            dd = int(re.sub(r"\D", "", day_el.get_text()) or 0)
            if not (1 <= mm <= 12 and 1 <= dd <= 31):
                continue

            about = inner.select_one(".c-scheduleList__about")
            event_name = lineup = open_t = start_t = adv = door = rawp = ""
            if about:
                lines = [x.strip() for x in about.get_text("\n", strip=True).split("\n") if x.strip()]
                # OPEN/ADV 以降は出演者ではない。最初の該当行の位置を境界にする。
                stop = next((i for i, ln in enumerate(lines)
                             if re.search(r"OPEN|START|ADV|DOOR|前売|料金|¥|￥", ln, re.I)), len(lines))
                if lines:
                    event_name = lines[0]
                    lineup = " / ".join(lines[1:stop])
                flat = " ".join(lines)
                open_t, start_t = parse_open_start(flat)
                pm = re.search(r"(?:ADV\s*/?\s*DOOR|前売|当日|料金)(.*)$", flat, re.I)
                if pm:
                    adv, door, rawp = parse_price(pm.group(1))

            raw.append(dict(mm=mm, dd=dd, name=event_name, lineup=lineup,
                            open_t=open_t, start_t=start_t, adv=adv, door=door, raw=rawp))
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
                    url=f"{self.venue.base_url}/schedule",
                ))
        self._cache = out
        return out
