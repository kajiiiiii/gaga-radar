# -*- coding: utf-8 -*-
"""GROWLY（京都・二条）パーサ。

構造（確認済み・2024-11で検証）:
  月ページ:  /schedule/?year=YYYY&month=MM   ← 年月はURLで指定できる（サーバ描画）
  <table id="js_schedule_table">
    <tr>                                  … 1日ぶん
      <th><p class="s_calendar_list_day">01</p><p>Fri</p></th>  … 日
      <td> <table><tbody>
        <tr class="normal">               … その日の1公演
          <td class="schedule_name">
            <h3><a href="./detail.html?id=7378" title="イベント名">イベント名</a></h3>
            <div class="s_artist_img"> …出演 :<br> A / B / C </div>
          </td>
          <td class="schedule_event_time">
            <table class="s_time_price">
              <tr><th>OPEN</th><td>18:00</td></tr>
              <tr><th>START</th><td>18:30</td></tr>
              ... (ADV/DOOR 等)
            </table>
          </td>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_price, split_artists


class GrowlyScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schedule/?year={year}&month={month:02d}"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        table = soup.select_one("#js_schedule_table")
        if not table:
            return []

        out: list[Appearance] = []
        # 直下の各 <tr>（=1日）を走査
        for day_tr in table.find_all("tr", recursive=False):
            day_el = day_tr.select_one(".s_calendar_list_day")
            if not day_el:
                continue
            dd = int(re.sub(r"\D", "", day_el.get_text()) or 0)
            if not (1 <= dd <= 31):
                continue
            date_s = f"{year:04d}-{month:02d}-{dd:02d}"

            for ev in day_tr.select("tr.normal"):
                name_td = ev.select_one(".schedule_name")
                if not name_td:
                    continue
                a = name_td.select_one("h3 a")
                event_name = (a.get("title") or a.get_text(strip=True)) if a else ""
                href = a["href"] if (a and a.has_attr("href")) else ""
                url_full = _abs_url(self.venue.base_url, href)

                # 出演者: 「出演 :」以降のテキスト
                artist_box = name_td.select_one(".s_artist_img")
                lineup = ""
                if artist_box:
                    txt = artist_box.get_text("\n", strip=True)
                    m = re.search(r"出演\s*[:：]?\s*(.+)", txt, re.S)
                    lineup = m.group(1) if m else ""

                open_t = start_t = adv = door = price_raw = ""
                time_tbl = ev.select_one(".s_time_price")
                if time_tbl:
                    pairs = {}
                    for row in time_tbl.select("tr"):
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            pairs[th.get_text(strip=True)] = td.get_text(strip=True)
                    open_t = _time(pairs.get("OPEN", ""))
                    start_t = _time(pairs.get("START", ""))
                    price_text = " ".join(
                        v for k, v in pairs.items() if k not in ("OPEN", "START", "")
                    )
                    if price_text.strip():
                        adv, door, price_raw = parse_price(price_text)

                for name in (split_artists(lineup) or [""]):
                    out.append(Appearance(
                        date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                        event_name=event_name, artist=name,
                        open_time=open_t, start_time=start_t,
                        price_advance=adv, price_door=door, price_raw=price_raw,
                        url=url_full,
                    ))
        return out


def _time(s: str) -> str:
    m = re.search(r"\d{1,2}:\d{2}", s or "")
    return m.group(0) if m else ""


def _abs_url(base: str, href: str) -> str:
    if not href:
        return f"{base}/schedule/"
    if href.startswith("http"):
        return href
    return f"{base}/schedule/{href.lstrip('./')}"
