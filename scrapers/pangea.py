# -*- coding: utf-8 -*-
"""Pangea（大阪・アメリカ村 / livepangea.com）パーサ。

構造（確認済み・2026-09時点）:
  1ページ (/schedule/) に今後の公演が日付順で全部載る（WordPress）。
  各公演ブロック = <div class="container-fluid"> の中に:
    <p class="live_mom">09/</p><p class="live_day">09</p>   … 月/日（年は無い→推定）
    <h4> … <a href="/live/xxx">イベント名</a></h4>
    <span class="badge ... rere">出演者</span> <p>A / B / C</p>
    <p><span>OPEN</span> 18:00 <span>START</span> 18:30 <span>PRICE</span> ADV ¥2500 …</p>

年はページに無いので、日付順＝今後、という前提で推定する（infer_years）。
1ページで全月ぶん取れるので、月ごとの取得はキャッシュから返す。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import (
    BaseScraper,
    fetch,
    infer_years,
    parse_price,
    split_artists,
)


class PangeaScraper(BaseScraper):

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
        for day_el in soup.select(".live_day"):
            block = day_el
            for _ in range(6):  # 公演ブロック(container-fluid)まで遡る
                block = block.parent
                if block is None:
                    break
                cls = block.get("class") or []
                if "container-fluid" in cls:
                    break
            if block is None:
                continue

            mom_el = block.select_one(".live_mom")
            mm = int(re.sub(r"\D", "", mom_el.get_text())) if mom_el else 0
            dd = int(re.sub(r"\D", "", day_el.get_text()) or 0)
            if not (1 <= mm <= 12 and 1 <= dd <= 31):
                continue

            title_a = block.select_one("h4 a")
            event_name = title_a.get_text(strip=True).strip('"“”') if title_a else ""
            url = title_a["href"] if (title_a and title_a.has_attr("href")) else f"{self.venue.base_url}/schedule/"

            # 出演者: 「出演者」バッジの直後の <p>
            lineup = ""
            for badge in block.select(".badge"):
                if "出演者" in badge.get_text():
                    p = badge.find_next("p")
                    if p:
                        lineup = p.get_text(" ", strip=True)
                    break

            # OPEN/START/PRICE はブロック全体テキストから拾う
            text = block.get_text(" ", strip=True)
            open_t = _find_time_after(text, "OPEN")
            start_t = _find_time_after(text, "START")
            adv = door = price_raw = ""
            pm = re.search(r"PRICE(.+)$", text)
            if pm:
                adv, door, price_raw = parse_price(pm.group(1))

            raw.append(dict(mm=mm, dd=dd, name=event_name, url=url, lineup=lineup,
                            open_t=open_t, start_t=start_t, adv=adv, door=door, raw=price_raw))
            months.append(mm)

        years = infer_years(months)

        out: list[Appearance] = []
        for e, y in zip(raw, years):
            date_s = f"{y:04d}-{e['mm']:02d}-{e['dd']:02d}"
            artists = split_artists(e["lineup"]) or [""]
            for name in artists:
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=e["name"], artist=name,
                    open_time=e["open_t"], start_time=e["start_t"],
                    price_advance=e["adv"], price_door=e["door"], price_raw=e["raw"],
                    url=e["url"],
                ))
        self._cache = out
        return out


def _find_time_after(text: str, label: str) -> str:
    m = re.search(label + r"[^0-9]{0,6}(\d{1,2}:\d{2})", text)
    return m.group(1) if m else ""
