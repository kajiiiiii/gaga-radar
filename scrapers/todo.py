# -*- coding: utf-8 -*-
"""未実装会場の受け皿。

個別パーサができるまでの仮置き。呼ばれても何も取得せず、空を返す。
実装する時は scrapers/<key>.py を作り、scrapers/__init__.py の
SCRAPER_TYPES に登録して venue.scraper を差し替える
（bassontop.py / pangea.py / growly.py が実装の参考になる）。
"""
from __future__ import annotations

from models import Appearance
from scrapers.base import BaseScraper


class TodoScraper(BaseScraper):
    def scrape_month(self, year: int, month: int) -> list[Appearance]:
        return []
