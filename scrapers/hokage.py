# -*- coding: utf-8 -*-
"""HOKAGE（大阪・心斎橋）パーサ。

構造（確認済み・2026-09時点）:
  /schedule/ に今後の公演が並ぶ（WordPress）。各公演:
    <article class="schedule-card">
      <p class="schedule-card__event-name">イベント名</p>
      <p class="schedule-card__performers">出演者</p>
      <span class="schedule-card__date">09.01</span>   ← 月.日（年なし→推定）
      <span class="schedule-card__day">TUE</span>
      <a class="schedule-card__btn" href="…">VIEW</a>

年はページに無いので日付順から推定（infer_years）。1ページ表示のため
過去バックフィルは不可（今後ぶんを蓄積する運用）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, infer_years, split_artists


class HokageScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        html = fetch(f"{self.venue.base_url}/schedule/")
        if not html:
            self._cache = []
            return self._cache
        soup = BeautifulSoup(html, "lxml")

        raw: list[dict] = []
        months: list[int] = []
        for card in soup.select(".schedule-card"):
            date_el = card.select_one(".schedule-card__date")
            if not date_el:
                continue
            md = re.search(r"(\d{1,2})\.(\d{1,2})", date_el.get_text())
            if not md:
                continue
            mm, dd = int(md.group(1)), int(md.group(2))

            name_el = card.select_one(".schedule-card__event-name")
            event_name = name_el.get_text(" ", strip=True) if name_el else ""

            perf_el = card.select_one(".schedule-card__performers")
            lineup = perf_el.get_text(" ", strip=True) if perf_el else ""

            btn = card.select_one("a.schedule-card__btn")
            url = btn["href"] if (btn and btn.has_attr("href")) else f"{self.venue.base_url}/schedule/"

            raw.append(dict(mm=mm, dd=dd, name=event_name, lineup=lineup, url=url))
            months.append(mm)

        years = infer_years(months)

        out: list[Appearance] = []
        for e, y in zip(raw, years):
            date_s = f"{y:04d}-{e['mm']:02d}-{e['dd']:02d}"
            for name in (split_artists(e["lineup"]) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=e["name"], artist=name, url=e["url"],
                ))
        self._cache = out
        return out
