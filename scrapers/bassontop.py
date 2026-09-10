# -*- coding: utf-8 -*-
"""
ベースオントップ系ライブハウスの共通パーサ。

対象（同一テンプレート）: 心斎橋VARON / 北堀江vijon / 堺東Goith /
  梅田BANGBOO / アメ村BEYOND / 梅田Zeela / アメ村DROP など。

構造（確認済み・2026-09時点）:
  月ページ:  {base}/schedule/calendar/{YYYY}/{MM}/
    <div class="container scheduleList">
      <ul>
        <li>
          <p class="day">2026.10.03(Sat)</p>
          <h1>イベント名</h1>
          <span class="artist ...">A / B / C</span>
          <a href=".../schedule/detail/48377" class="btnStyle01">MORE</a>
        </li>
  詳細ページ (OPEN/START・料金はこちらにある):
    <dl class="openTime"><dd>17:30/18:30</dd></dl>
    <dl class="price"><dd>前売：￥2000 当日：￥2500 （1D別）</dd></dl>
"""
from __future__ import annotations

from bs4 import BeautifulSoup

import config
from models import Appearance, make_event_id
from scrapers.base import (
    BaseScraper,
    fetch,
    parse_date,
    parse_open_start,
    parse_price,
    split_artists,
)


class BassOnTopScraper(BaseScraper):

    def month_url(self, year: int, month: int) -> str:
        return f"{self.venue.base_url}/schedule/calendar/{year:04d}/{month:02d}/"

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        html = fetch(self.month_url(year, month))
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")

        # 詳細取得を1公演1回で済ませるためのキャッシュ (url -> (open,start,adv,door,raw))
        detail_cache: dict[str, tuple[str, str, str, str, str]] = {}
        out: list[Appearance] = []

        list_box = soup.select_one(".scheduleList")
        if not list_box:
            return []

        for li in list_box.select("li"):
            day_el = li.select_one(".day")
            date = parse_date(day_el.get_text()) if day_el else None
            if not date:
                continue

            title_el = li.select_one("h1")
            event_name = title_el.get_text(strip=True) if title_el else ""

            artist_el = li.select_one(".artist")
            artists = split_artists(artist_el.get_text(" ", strip=True)) if artist_el else []

            more = li.select_one("a.btnStyle01")
            detail_url = more["href"] if (more and more.has_attr("href")) else self.month_url(year, month)

            # 既にDBにある公演は詳細ページを取りに行かない（日次の負荷を大幅削減）。
            # 重複除去で最終的に落ちるので open/start/料金 は空のままで良い。
            known = make_event_id(self.venue.name, date, event_name) in self.known_event_ids

            open_t = start_t = adv = door = raw = ""
            if config.FETCH_DETAILS and detail_url and not known:
                if detail_url not in detail_cache:
                    detail_cache[detail_url] = self._scrape_detail(detail_url)
                open_t, start_t, adv, door, raw = detail_cache[detail_url]

            if not artists:
                # 出演者が取れない公演も、公演自体は1行残す（出演者空欄）
                artists = [""]

            for name in artists:
                out.append(Appearance(
                    date=date,
                    venue=self.venue.name,
                    prefecture=self.venue.prefecture,
                    event_name=event_name,
                    artist=name,
                    open_time=open_t,
                    start_time=start_t,
                    price_advance=adv,
                    price_door=door,
                    price_raw=raw,
                    url=detail_url,
                ))
        return out

    def _scrape_detail(self, url: str) -> tuple[str, str, str, str, str]:
        html = fetch(url)
        if not html:
            return "", "", "", "", ""
        soup = BeautifulSoup(html, "lxml")

        open_t = start_t = ""
        ot = soup.select_one(".openTime")
        if ot:
            dd = ot.select_one("dd")
            if dd:
                open_t, start_t = parse_open_start(dd.get_text(" ", strip=True))

        adv = door = raw = ""
        pr = soup.select_one(".price")
        if pr:
            dd = pr.select_one("dd")
            if dd:
                adv, door, raw = parse_price(dd.get_text(" ", strip=True))

        return open_t, start_t, adv, door, raw
