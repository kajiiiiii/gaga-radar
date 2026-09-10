# -*- coding: utf-8 -*-
"""CSV入出力と重複排除。

- Excelで文字化けしないよう utf-8-sig（BOM付き）で書き出す。
- event_artist_id をキーに重複を除く。
"""
from __future__ import annotations

import csv
from pathlib import Path

from models import COLUMNS, Appearance


def write_csv(appearances: list[Appearance], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for a in appearances:
            w.writerow(a.to_row())


def load_existing_ids(path: Path) -> set[str]:
    """既存CSVから event_artist_id の集合を読む（無ければ空）。"""
    if not path.exists():
        return set()
    ids: set[str] = set()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            v = row.get("event_artist_id")
            if v:
                ids.add(v)
    return ids


def append_dedup(appearances: list[Appearance], path: Path) -> list[Appearance]:
    """既存IDに無いものだけCSVへ追記し、実際に追加した行を返す。"""
    existing = load_existing_ids(path)
    seen = set(existing)
    new_rows: list[Appearance] = []
    for a in appearances:
        aid = a.event_artist_id
        if aid in seen:
            continue
        seen.add(aid)
        new_rows.append(a)

    if not new_rows:
        return []

    write_header = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(COLUMNS)
        for a in new_rows:
            w.writerow(a.to_row())
    return new_rows


def dedup(appearances: list[Appearance]) -> list[Appearance]:
    """リスト内の重複（同一 event_artist_id）を除去。"""
    seen, out = set(), []
    for a in appearances:
        aid = a.event_artist_id
        if aid not in seen:
            seen.add(aid)
            out.append(a)
    return out
