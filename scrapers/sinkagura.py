# -*- coding: utf-8 -*-
"""新神楽（大阪・アメリカ村）パーサ。

Jimdo製サイト。月サブページ /schedule/YYYY-MM/ に、フリーテキストで公演が並ぶ:
    2026.9.01(Tue)SINKAGURA 5F      ← 日付行（ここで公演を区切る）
    ちゃんとせぇ！                    ← イベント名（日付の次行）
    OPEN/START 19:00/19:30
    ADV/DOOR ¥1000/¥1500
    まーくん(Bayside Blow)            ← 出演者（1行1組）
    小坂慶太
    …

構造タグが無いので、日付行で区切ってテキストを解析する。年月はURLで指定。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists

_DATE_LINE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})\s*\(")


class SinkaguraScraper(BaseScraper):

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        url = f"{self.venue.base_url}/schedule/{year:04d}-{month:02d}/"
        html = fetch(url)
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n")
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

        # 日付行の位置で公演ブロックに分割
        idxs = [i for i, ln in enumerate(lines) if _DATE_LINE.match(ln)]
        out: list[Appearance] = []
        for n, start in enumerate(idxs):
            end = idxs[n + 1] if n + 1 < len(idxs) else len(lines)
            block = lines[start:end]
            dm = _DATE_LINE.match(block[0])
            y, mo, d = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
            if (y, mo) != (year, month):
                continue
            date_s = f"{y:04d}-{mo:02d}-{d:02d}"

            event_name = ""
            open_t = start_t = adv = door = raw = ""
            artists: list[str] = []
            for ln in block[1:]:
                if re.search(r"OPEN\s*/?\s*START", ln, re.I):
                    open_t, start_t = parse_open_start(ln)
                elif re.search(r"(ADV|DOOR|前売|当日|¥|￥|円|飲み放題|チャージ)", ln):
                    if not raw:
                        adv, door, raw = parse_price(ln)
                elif not event_name:
                    event_name = ln
                else:
                    artists.extend(split_artists(ln))

            for name in (artists or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=event_name, artist=name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        return out
