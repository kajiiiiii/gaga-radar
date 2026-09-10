# -*- coding: utf-8 -*-
"""Live House ANIMA（大阪・アメリカ村）パーサ。

ANIMA は WordPress + Event Organiser プラグインで、iCal フィードを公開している:
  {base}/?feed=eo-events
これを使うと 2019年〜の全公演が「日付・イベント名・URL」付きで構造化されて取れる
（HTML解析より確実）。過去バックフィルも可能。

制約: フィードには出演者(ラインナップ)が入っていない。出演者は各公演の
  詳細ページ(URL)にあるため、ここでは日付・イベント名・URLまでを取得する
  （出演者は空欄）。出演者も埋めたい場合は詳細ページ解析を追加する（TODO）。
"""
from __future__ import annotations

import re

from models import Appearance
from scrapers.base import BaseScraper, fetch


class AnimaScraper(BaseScraper):

    def __init__(self, venue):
        super().__init__(venue)
        self._cache: list[Appearance] | None = None

    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        prefix = f"{year:04d}-{month:02d}"
        return [a for a in self._load_all() if a.date.startswith(prefix)]

    def _load_all(self) -> list[Appearance]:
        if self._cache is not None:
            return self._cache
        text = fetch(f"{self.venue.base_url}/?feed=eo-events")
        if not text:
            self._cache = []
            return self._cache

        text = _unfold_ical(text)
        out: list[Appearance] = []
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
            fields = dict(re.findall(r"^([A-Z][A-Z0-9-]*)(?:;[^:]*)?:(.*)$", block, re.M))
            dt = fields.get("DTSTART", "")
            dm = re.search(r"(\d{4})(\d{2})(\d{2})", dt)
            if not dm:
                continue
            date_s = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
            name = _ical_unescape(fields.get("SUMMARY", "")).strip()
            url = fields.get("URL", "").strip()
            out.append(Appearance(
                date=date_s, venue=self.venue.name, prefecture=self.venue.prefecture,
                event_name=name, artist="", url=url,
            ))
        self._cache = out
        return out


def _unfold_ical(text: str) -> str:
    # iCalの折り返し（行頭スペース/タブで継続）を解除
    return re.sub(r"\r?\n[ \t]", "", text)


def _ical_unescape(s: str) -> str:
    return s.replace("\\,", ",").replace("\\;", ";").replace("\\n", " ").replace("\\\\", "\\")
