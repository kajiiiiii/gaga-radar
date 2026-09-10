# -*- coding: utf-8 -*-
"""iCalフィード汎用パーサ（Event Organiser / The Events Calendar 等）。

WordPressのイベント系プラグインはiCalフィードを出すことが多く、HTML解析より確実。
  - AFTER BEAT (The Events Calendar): /afterbeat/?ical=1  … DESCRIPTIONに act:/OPEN/料金あり（出演者まで取れる）
  - SUNHALL (Event Organiser): /?feed=eo-events           … 日付/タイトル/時間/料金（出演者は不定）

VEVENTごとに DTSTART(日付) / SUMMARY(イベント名) / DESCRIPTION(出演者・時間・料金) を取る。
過去も含め全件取れるため、月フィルタはキャッシュから行う。
"""
from __future__ import annotations

import re

from models import Appearance
from scrapers.base import BaseScraper, fetch, parse_open_start, parse_price, split_artists

# venue.key -> フィードのパス
FEED_PATHS = {
    "afterbeat": "/afterbeat/?ical=1",
    "sunhall": "/?feed=eo-events",
    "anima": "/?feed=eo-events",
}

_ACT = re.compile(r"^(?:act|ACT|出演|LIVE|LINE\s*UP|lineup)\s*[:：]?\s*$", re.I)
_STOP = re.compile(r"(OPEN|START|OP[\.\s：]|ST[\.\s：]|ADV|DOOR|料金|前売|当日|¥|￥|円|\d{1,2}:\d{2}|チケット|ticket)", re.I)


class ICalScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def _feed_url(self) -> str:
        return self.venue.base_url + FEED_PATHS.get(self.venue.key, "/?feed=eo-events")

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        text = fetch(self._feed_url())
        if not text:
            self._cache = []
            return self._cache
        text = re.sub(r"\r?\n[ \t]", "", text)  # unfold

        out: list[Appearance] = []
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
            fields = dict(re.findall(r"^([A-Z][A-Z0-9-]*)(?:;[^:]*)?:(.*)$", block, re.M))
            dm = re.match(r"(\d{4})(\d{2})(\d{2})", fields.get("DTSTART", ""))
            if not dm:
                continue
            date_s = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            name = _unescape(fields.get("SUMMARY", "")).strip()
            desc = _unescape(fields.get("DESCRIPTION", ""))
            url = fields.get("URL", "").strip() or self.venue.base_url

            open_t, start_t = parse_open_start(desc)
            adv = door = raw = ""
            pm = re.search(r"(?:ADV|DOOR|前売|当日|料金)(.{0,40})", desc, re.I)
            if pm:
                adv, door, raw = parse_price(pm.group(1))

            artists = _lineup_from_desc(desc)
            for a_name in (artists or [""]):
                out.append(Appearance(
                    date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                    event_name=name, artist=a_name,
                    open_time=open_t, start_time=start_t,
                    price_advance=adv, price_door=door, price_raw=raw,
                    url=url,
                ))
        self._cache = out
        return out


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _lineup_from_desc(desc: str) -> list[str]:
    """DESCRIPTION内の 'act:' 等の見出し以降、時間/料金が出るまでの行を出演者として拾う。"""
    lines = [ln.strip() for ln in desc.split("\n")]
    out: list[str] = []
    collecting = False
    for ln in lines:
        if not ln:
            continue
        if _ACT.match(ln):
            collecting = True
            continue
        if collecting:
            if _STOP.search(ln):
                break
            out.extend(split_artists(ln))
    return out
