# -*- coding: utf-8 -*-
"""
データモデル。

重要な設計判断:
  「1公演1行」ではなく「1出演者1行」で持つ。
  こうすることで「Band-A は90日で何本出たか」を後から SQL/集計で簡単に出せる。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime

# スプレッドシート「公演DB」の列順（ヘッダー）。この順で append する。
COLUMNS = [
    "event_artist_id",  # 出演者×公演の一意ID（重複防止キー）
    "event_id",         # 公演単位のID（同じ公演の出演者をまとめる用）
    "公演日",            # YYYY-MM-DD
    "会場",
    "都道府県",
    "イベント名",
    "出演者",            # 1名
    "OPEN",
    "START",
    "前売",
    "当日",
    "料金備考",          # 元の料金文字列（自動分割に失敗した時の保険）
    "URL",
    "取得日時",
]


def _hash(*parts: str) -> str:
    raw = "\x1f".join((p or "").strip() for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_event_id(venue: str, date: str, event_name: str) -> str:
    """Appearance を作る前に公演IDを求める（増分取得で詳細フェッチ要否を判定する用）。

    Appearance.event_id と同じ規則。詳細ページを取りに行く前に「既知の公演か」を
    判定できるようにするためのヘルパー。
    """
    return _hash(venue, date, event_name)


@dataclass
class Appearance:
    """1出演者×1公演＝1行。"""
    date: str            # YYYY-MM-DD
    venue: str
    prefecture: str
    event_name: str
    artist: str
    open_time: str = ""
    start_time: str = ""
    price_advance: str = ""
    price_door: str = ""
    price_raw: str = ""
    url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def event_id(self) -> str:
        # 会場+日付+イベント名 で公演を一意化
        return _hash(self.venue, self.date, self.event_name)

    @property
    def event_artist_id(self) -> str:
        # さらに出演者を加えて出演1件を一意化（＝重複防止キー）
        return _hash(self.venue, self.date, self.event_name, self.artist)

    def to_row(self) -> list[str]:
        return [
            self.event_artist_id,
            self.event_id,
            self.date,
            self.venue,
            self.prefecture,
            self.event_name,
            self.artist,
            self.open_time,
            self.start_time,
            self.price_advance,
            self.price_door,
            self.price_raw,
            self.url,
            self.scraped_at,
        ]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_id"] = self.event_id
        d["event_artist_id"] = self.event_artist_id
        return d
