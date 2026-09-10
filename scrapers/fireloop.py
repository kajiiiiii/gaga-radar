# -*- coding: utf-8 -*-
"""寺田町Fireloop（大阪）パーサ。

構造（確認済み・2026-09時点）:
  /schedule_now.shtml に今後の公演が並ぶ。各公演:
    <div class="half-page left" id=0902>
      <h2 class=datef>09/02<div class=weekday>FRI</div></h2>   ← 月/日（年なし→推定）
      <div class=title>イベント名</div>
      <div class=cast>出演者A<br>出演者B…</div>
      <h4 class=time-fee>open 18:30 / start 19:30<br>前売 3,000円 / 当日 4,000円…</h4>

年はページに無いので日付順から推定（infer_years）。1ページ表示のため
過去バックフィルは不可（今後ぶんを蓄積する運用）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import (
    BaseScraper,
    fetch,
    infer_years,
    parse_open_start,
    parse_price,
    split_artists,
)


class FireloopScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/schedule_now.shtml")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        raw: list[dict] = []
        months: list[int] = []
        for blk in soup.select(".half-page.left"):
            datef = blk.select_one(".datef")
            if not datef:
                continue
            md = re.search(r"(\d{1,2})/(\d{1,2})", datef.get_text())
            if not md:
                continue
            mm, dd = int(md.group(1)), int(md.group(2))

            title_el = blk.select_one(".title")
            event_name = title_el.get_text(" ", strip=True) if title_el else ""

            cast = blk.select_one(".cast")
            lineup = cast.get_text("\n", strip=True) if cast else ""

            fee = blk.select_one(".time-fee")
            open_t = start_t = adv = door = raw_price = ""
            if fee:
                ftext = fee.get_text(" ", strip=True)
                open_t, start_t = parse_open_start(ftext)
                pm = re.search(r"(前売.*)$", ftext)
                if pm:
                    adv, door, raw_price = parse_price(pm.group(1))

            raw.append(dict(mm=mm, dd=dd, name=event_name, lineup=lineup,
                            open_t=open_t, start_t=start_t, adv=adv, door=door, raw=raw_price))
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
                    url=f"{self.venue.base_url}/schedule_now.shtml",
                ))
        self._cache = out
        return out
