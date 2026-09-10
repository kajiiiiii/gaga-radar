# -*- coding: utf-8 -*-
"""スクレイパのレジストリ。

venue.scraper（種別名）→ パーサクラス の対応。
新しい会場を追加するときは:
  - ベースオントップ系なら venues.py に1行足すだけ（scraper="bassontop"）。
  - 独自サイトなら scrapers/<name>.py を作り、下の SCRAPER_TYPES に登録する。
"""
from __future__ import annotations

from scrapers.base import BaseScraper
from scrapers.bassontop import BassOnTopScraper
from scrapers.pangea import PangeaScraper
from scrapers.varit import VaritScraper
from scrapers.growly import GrowlyScraper
from scrapers.knave import KnaveScraper
from scrapers.socore import SocoreScraper
from scrapers.hokage import HokageScraper
from scrapers.anima import AnimaScraper
from scrapers.nano import NanoScraper
from scrapers.mojo import MojoScraper
from scrapers.fireloop import FireloopScraper
from scrapers.bronze import BronzeScraper
from scrapers.dewey import DeweyScraper
from scrapers.neverland import NeverlandScraper
from scrapers.padoma import PadomaScraper
from scrapers.mele import MeleScraper
from scrapers.taitora import TaitoraScraper
from scrapers.sinkagura import SinkaguraScraper
from scrapers.kingsx import KingsxScraper
from scrapers.muse import MuseScraper
from scrapers.musearm import MuseArmScraper
from scrapers.ical import ICalScraper
from scrapers.janus import JanusScraper
from scrapers.bflat import BflatScraper
from scrapers.clubgate import ClubgateScraper
from scrapers.atlantiqs import AtlantiqsScraper
from scrapers.todo import TodoScraper
from venues import Venue

SCRAPER_TYPES: dict[str, type[BaseScraper]] = {
    "bassontop": BassOnTopScraper,
    "pangea": PangeaScraper,
    "varit": VaritScraper,
    "growly": GrowlyScraper,
    "knave": KnaveScraper,
    "socore": SocoreScraper,
    "hokage": HokageScraper,
    "anima": AnimaScraper,
    "nano": NanoScraper,
    "mojo": MojoScraper,
    "fireloop": FireloopScraper,
    "bronze": BronzeScraper,
    "dewey": DeweyScraper,
    "neverland": NeverlandScraper,
    "padoma": PadomaScraper,
    "mele": MeleScraper,
    "taitora": TaitoraScraper,
    "sinkagura": SinkaguraScraper,
    "kingsx": KingsxScraper,
    "muse": MuseScraper,
    "musearm": MuseArmScraper,
    "ical": ICalScraper,
    "janus": JanusScraper,
    "bflat": BflatScraper,
    "clubgate": ClubgateScraper,
    "atlantiqs": AtlantiqsScraper,
    "todo": TodoScraper,
}


def get_scraper(venue: Venue) -> BaseScraper:
    cls = SCRAPER_TYPES.get(venue.scraper)
    if cls is None:
        raise ValueError(f"未知のスクレイパ種別: {venue.scraper}（venue={venue.key}）")
    return cls(venue)
