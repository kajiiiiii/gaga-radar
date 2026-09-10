# -*- coding: utf-8 -*-
"""神戸VARIT.（兵庫）パーサ。

構造（確認済み・2026-09時点）:
  一覧 (/schedule/) は「今後の公演」を日付順で表示（WordPress）。
    各公演 = <div class="livecontent">
        <h4 class="title"><a href="/project/…">イベント名</a></h4>
        <div class="details"> 出演者テキスト </div>
      ※ 一覧には日(DD)しか無く、月・年が無い。
  詳細 (/project/…) の本文に「09/11 Fri」「OPEN/START 18:30 / 19:00」がある。
    → 月・日は詳細ページから取得し、年は日付順の前提で推定する。

注意: VARIT.の一覧は直近ぶんしか出さないため、過去のバックフィルには不向き
      （出た公演をその都度拾って蓄積していく運用になる）。出演者情報も
      一覧の details が薄い公演があり、その場合は出演者空欄で公演だけ残す。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import (
    BaseScraper,
    fetch,
    infer_years,
    split_artists,
)

_WEEK = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"


class VaritScraper(BaseScraper):

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
        for lc in soup.select(".livecontent"):
            a = lc.select_one(".title a")
            if not a or not a.has_attr("href"):
                continue  # 「イベント未定」等のプレースホルダは <a> 無し
            name = a.get_text(strip=True)
            url = a["href"]
            details_el = lc.select_one(".details")
            lineup = details_el.get_text(" ", strip=True) if details_el else ""

            mm, dd, open_t, start_t, adv, door, praw = self._scrape_detail(url)
            if mm is None:
                continue
            raw.append(dict(mm=mm, dd=dd, name=name, url=url, lineup=lineup,
                            open_t=open_t, start_t=start_t, adv=adv, door=door, raw=praw))
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
                    url=e["url"],
                ))
        self._cache = out
        return out

    def _scrape_detail(self, url: str):
        html = fetch(url)
        if not html:
            return (None, None, "", "", "", "", "")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)

        mm = dd = None
        md = re.search(rf"(\d{{1,2}})/(\d{{1,2}})\s*{_WEEK}", text)
        if md:
            mm, dd = int(md.group(1)), int(md.group(2))
        if not mm:
            return (None, None, "", "", "", "", "")

        open_t = start_t = ""
        ot = re.search(r"OPEN\s*/?\s*START\s*(\d{1,2}:\d{2})\s*/\s*(\d{1,2}:\d{2})", text)
        if ot:
            open_t, start_t = ot.group(1), ot.group(2)
        else:
            times = re.findall(r"\d{1,2}:\d{2}", text)
            if len(times) >= 2:
                open_t, start_t = times[0], times[1]

        # VARIT.の詳細は¥表記が不安定で、年号(2026年…)を金額と誤認しやすい。
        # 明示的に ¥/￥/円 が付いた金額だけを採用し、無ければ空欄にする。
        adv = door = praw = ""
        yen = re.findall(r"[¥￥]\s?(\d[\d,]{2,})|(\d[\d,]{2,})\s?円", text)
        amounts = [a or b for a, b in yen]
        amounts = [x.replace(",", "") for x in amounts if int(x.replace(",", "")) >= 500]
        if amounts:
            adv = amounts[0]
            door = amounts[1] if len(amounts) >= 2 else ""
            praw = " / ".join(amounts[:3])
        return (mm, dd, open_t, start_t, adv, door, praw)
