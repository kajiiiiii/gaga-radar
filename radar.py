# -*- coding: utf-8 -*-
"""
アーティストDB再集計 & 発掘候補スコアリング。

公演DB（1出演者1行）を読み込み、アーティスト単位に集計する:
  - 出演回数 / 出演会場数 / 都道府県数 / 初・直近出演日
  - 直近90日 と その前90日 の出演数、増加率（＝勢い / momentum）
  - 共演者数（共演ネットワークの種）

「増加率が高い × 会場/エリアが広がっている」アーティストが発掘候補。
数字で"観に行く候補"を見つけ、最終判断は自分たちの目で、という使い方を想定。
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import config
from scrapers.base import is_noise_artist, normalize_artist

ARTIST_HEADER = [
    "アーティスト",
    "出演回数",
    "会場数",
    "都道府県数",
    "初出演日",
    "直近出演日",
    "直近90日",
    "前90日",
    "増加率",
    "共演者数",
    "主な会場",
    "発掘スコア",
]


def load_appearances(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)]


def _pdate(s: str) -> date | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def build_artist_summary(rows: list[dict], as_of: date | None = None,
                         window: int | None = None) -> list[list]:
    as_of = as_of or date.today()
    win = window or config.RADAR_WINDOW_DAYS
    recent_from = as_of - timedelta(days=win)
    prev_from = as_of - timedelta(days=2 * win)

    dates: dict[str, list[date]] = defaultdict(list)
    venues: dict[str, set] = defaultdict(set)
    prefs: dict[str, set] = defaultdict(set)
    venue_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    event_members: dict[str, set] = defaultdict(set)   # event_id -> {正規化キー}
    artist_events: dict[str, set] = defaultdict(set)    # 正規化キー -> {event_id}
    display_counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))  # キー -> 表記別出現数

    for r in rows:
        raw = str(r.get("出演者") or "").strip()
        if not raw or is_noise_artist(raw):
            continue
        key = normalize_artist(raw)   # 名寄せキー（表記ゆれ吸収）
        display_counts[key][raw] += 1
        d = _pdate(r.get("公演日", ""))
        venue = r.get("会場", "")
        pref = r.get("都道府県", "")
        eid = r.get("event_id", "")
        if d:
            dates[key].append(d)
        venues[key].add(venue)
        prefs[key].add(pref)
        venue_counts[key][venue] += 1
        if eid:
            event_members[eid].add(key)
            artist_events[key].add(eid)

    summary: list[list] = []
    for key, ds in dates.items():
        # 表示名は最頻の表記を採用
        display = max(display_counts[key].items(), key=lambda kv: kv[1])[0]
        ds_sorted = sorted(ds)
        total = len(ds_sorted)
        recent = sum(1 for d in ds_sorted if recent_from < d <= as_of)
        prev = sum(1 for d in ds_sorted if prev_from < d <= recent_from)
        growth = round(recent / prev, 2) if prev else (float(recent) if recent else 0.0)

        # 共演者数
        co: set = set()
        for eid in artist_events[key]:
            co |= event_members[eid]
        co.discard(key)

        main_venue = max(venue_counts[key].items(), key=lambda kv: kv[1])[0] if venue_counts[key] else ""

        # 発掘スコア: 勢い(増加) × 活動範囲(会場・エリア)。無名で急拡大を拾う狙い。
        score = round(
            growth * 2.0
            + len(venues[key]) * 1.0
            + len(prefs[key]) * 1.5
            + recent * 0.5,
            2,
        )

        summary.append([
            display,
            total,
            len(venues[key]),
            len(prefs[key]),
            ds_sorted[0].isoformat(),
            ds_sorted[-1].isoformat(),
            recent,
            prev,
            growth,
            len(co),
            main_venue,
            score,
        ])

    # 発掘スコア降順
    summary.sort(key=lambda row: row[-1], reverse=True)
    return summary


def co_performers(rows: list[dict], artist: str) -> list[tuple[str, int]]:
    """指定アーティストの共演者を共演回数の多い順に返す（共演ネットワーク探索用）。"""
    event_members: dict[str, set] = defaultdict(set)
    artist_events: dict[str, set] = defaultdict(set)
    display: dict[str, dict] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        raw = str(r.get("出演者") or "").strip()
        eid = str(r.get("event_id", ""))
        if raw and eid:
            key = normalize_artist(raw)
            display[key][raw] += 1
            event_members[eid].add(key)
            artist_events[key].add(eid)
    target = normalize_artist(artist)
    counter: dict[str, int] = defaultdict(int)
    for eid in artist_events.get(target, set()):
        for other in event_members[eid]:
            if other != target:
                counter[other] += 1
    best = lambda k: max(display[k].items(), key=lambda kv: kv[1])[0]
    return sorted(((best(k), n) for k, n in counter.items()), key=lambda kv: kv[1], reverse=True)
