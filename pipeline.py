# -*- coding: utf-8 -*-
"""スクレイピングの共通処理（backfill / daily から使う）。"""
from __future__ import annotations

from models import Appearance
from scrapers import get_scraper
from store.csv_store import dedup
from venues import Venue


def scrape_venues(
    venues: list[Venue],
    start: tuple[int, int],
    end: tuple[int, int],
    known_event_ids: set[str] | None = None,
) -> list[Appearance]:
    all_rows: list[Appearance] = []
    for v in venues:
        print(f"[{v.name}] ({v.scraper}) {start[0]}/{start[1]:02d} 〜 {end[0]}/{end[1]:02d}")
        scraper = get_scraper(v)
        if known_event_ids:
            # 既知公演は詳細ページを再取得しない（対応スクレイパのみ効く）
            scraper.known_event_ids = known_event_ids
        all_rows.extend(scraper.scrape_range(start, end))
    rows = dedup(all_rows)
    print(f"== 合計 {len(rows)} 出演（重複除去後） ==")
    return rows
