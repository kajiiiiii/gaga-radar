# -*- coding: utf-8 -*-
"""SOCORE FACTORY（大阪）パーサ。

構造（確認済み・2026-09時点）:
  /schedule/ に今後の公演が並ぶ（WordPress）。各公演:
    <div class="schedule">
      <a class="e-left" href=".../schedule/2026/09/01/slug/">…</a>  ← URLに日付
      <div class="e-center"><p class="days">01</p><p class="day">Tue</p></div>
      <a href="…"><div class="e-right"><h3>イベント名</h3>
        <p class="act"><span class="lives">Act:</span>■LIVE\nバンドA\n■DJ\n…</p>

日付はURL（/YYYY/MM/DD/）から確定。年推定は不要。
1ページ表示のため過去バックフィルは不可（今後ぶんを蓄積する運用）。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, split_artists

_URL_DATE = re.compile(r"/schedule/(\d{4})/(\d{2})/(\d{2})/")


class SocoreScraper(BaseScraper):

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

        out: list[Appearance] = []
        for blk in soup.select(".schedule"):
            link = blk.select_one("a[href*='/schedule/20']")
            if not link:
                continue
            m = _URL_DATE.search(link["href"])
            if not m:
                continue
            date_s = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

            h3 = blk.select_one(".e-right h3")
            event_name = h3.get_text(" ", strip=True) if h3 else ""

            act = blk.select_one(".act")
            lineup = _clean_act(act.get_text("\n", strip=True)) if act else ""

            for name in (split_artists(lineup) or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name, url=link["href"],
                ))
        self._cache = out
        return out


def _clean_act(text: str) -> str:
    """'Act:' と ■カテゴリ見出し(■LIVE/■DJ等)を除き、出演者だけを / 区切りにする。"""
    text = re.sub(r"^\s*Act\s*[:：]?", "", text)
    lines = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if not ln or ln.startswith("■") or ln.startswith("●"):
            continue
        lines.append(ln)
    return " / ".join(lines)
