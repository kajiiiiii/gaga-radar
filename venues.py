# -*- coding: utf-8 -*-
"""
会場マスタ。

`scraper` は scrapers/ 内のどのパーサを使うか:
- "bassontop": ベースオントップ系の共通テンプレート（1本で複数会場）。
- "pangea"/"varit"/"growly": 実装済みの個別パーサ。
- "todo": 未実装（各サイト専用パーサが必要）。パイプラインでは自動スキップ。

`verified=True` は実際に取得できることを確認済みの会場。
`priority` は着手優先度（A/B/C）。個別パーサはこの順で作っていく。
`base_url` は末尾スラッシュなし。空文字は「URL未確定（要調査）」。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Venue:
    key: str
    name: str
    prefecture: str
    scraper: str
    base_url: str
    verified: bool = False
    priority: str = "A"


VENUES: list[Venue] = [
    # ============================ 大阪府 ============================
    # ---- ベースオントップ系（共通テンプレート・確認済み）----
    Venue("varon",  "心斎橋VARON", "大阪府", "bassontop", "https://osaka-varon.jp", verified=True, priority="A"),
    Venue("vijon",  "北堀江club vijon", "大阪府", "bassontop", "https://vijon.jp", verified=True, priority="A"),
    Venue("beyond", "アメリカ村BEYOND", "大阪府", "bassontop", "https://beyond-osaka.jp", verified=True, priority="A"),
    Venue("drop",   "アメリカ村DROP", "大阪府", "bassontop", "https://clubdrop.jp", verified=True, priority="A"),
    Venue("zeela",  "梅田Zeela", "大阪府", "bassontop", "https://osaka-zeela.jp", verified=True, priority="A"),
    Venue("goith",  "堺東Goith", "大阪府", "bassontop", "https://goith.jp", verified=True, priority="A"),
    Venue("bangboo", "梅田BANGBOO", "大阪府", "bassontop", "https://bangboo.jp", verified=True, priority="A"),

    # ---- 個別パーサ（実装済み）----
    Venue("pangea", "Live House Pangea", "大阪府", "pangea", "https://livepangea.com", verified=True, priority="A"),

    # ---- 大阪 A（要個別パーサ）----
    Venue("bronze",   "心斎橋BRONZE", "大阪府", "bronze", "http://osakabronze.com", verified=True, priority="A"),
    Venue("shinkagura", "新神楽", "大阪府", "sinkagura", "https://sinkagura.jimdofree.com", verified=True, priority="A"),
    Venue("hokage",   "HOKAGE", "大阪府", "hokage", "https://musicbarhokage.net", verified=True, priority="A"),
    Venue("anima",    "Live House ANIMA", "大阪府", "anima", "https://liveanima.jp", verified=True, priority="A"),
    Venue("atlantiqs", "AtlantiQs", "大阪府", "atlantiqs", "https://atlantiqs.com", verified=True, priority="A"),
    Venue("secondline", "LIVE SQUARE 2nd LINE", "大阪府", "todo", "http://2ndline.jp", priority="A"),
    Venue("knave",    "南堀江knave", "大阪府", "knave", "http://knave.co.jp", verified=True, priority="A"),
    Venue("fireloop", "寺田町Fireloop", "大阪府", "fireloop", "https://fireloop.net", verified=True, priority="A"),
    Venue("socore",   "SOCORE FACTORY", "大阪府", "socore", "https://socorefactory.com", verified=True, priority="A"),
    Venue("mele",     "難波Mele", "大阪府", "mele", "https://namba-mele.com", verified=True, priority="A"),

    # ---- 大阪 B（要個別パーサ）----
    Venue("osakamuse", "OSAKA MUSE", "大阪府", "muse", "http://osaka.muse-live.com", verified=True, priority="B"),
    # 以下URL調査済み（次バッチ実装予定）。末尾は検出したCMS/プラグイン。
    Venue("janus",    "Music Club JANUS", "大阪府", "janus", "https://janusosaka.com", verified=True, priority="B"),
    Venue("fanjtwice", "FANJtwice", "大阪府", "todo", "http://www.fanj-twice.com", priority="B"),             # 公演掲載が少なめ
    Venue("sunhall",  "SUNHALL", "大阪府", "ical", "https://sunhall.jp", verified=True, priority="B"),          # Event Organiser iCal（出演者は不定）
    Venue("kingcobra", "KING COBRA", "大阪府", "todo", "", priority="B"),
    Venue("hillspan", "hillsパン工場", "大阪府", "todo", "", priority="B"),
    # ESAKA MUSE は arm-live系だが schedule.html が単一ページ・日のみで月が曖昧。要追加対応。
    Venue("esakamuse", "ESAKA MUSE", "大阪府", "todo", "http://muse-live.com/esaka", priority="B"),
    # CLAPPER: トップにスケジュールリンクが無くJS描画の可能性。別アプローチ要。
    Venue("clapper",  "アメリカ村CLAPPER", "大阪府", "todo", "https://clapper.jp", priority="B"),
    Venue("ticktuck", "堺Tick-Tuck", "大阪府", "todo", "https://tick-tuck.wixsite.com/tick-tuck", priority="B"),  # Wix(月別ページ)
    Venue("jacklion", "茨木JACK LION", "大阪府", "todo", "", priority="B"),
    Venue("remembers", "枚方sweet music ReMEMBERS", "大阪府", "todo", "", priority="B"),

    # ============================ 兵庫県 ============================
    Venue("varit",   "神戸VARIT.", "兵庫県", "varit", "https://varit.jp", verified=True, priority="A"),
    Venue("taiyototora", "music zoo KOBE 太陽と虎", "兵庫県", "taitora", "https://taitora.com", verified=True, priority="A"),
    # 神戸ART HOUSE は閉店のため登録から除外。
    Venue("kingsx",   "KINGSX", "兵庫県", "kingsx", "https://kingsx.info", verified=True, priority="A"),
    Venue("padoma",   "live music club PADOMA", "兵庫県", "padoma", "https://padoma.jp", verified=True, priority="A"),
    # 尼崎tora は WordPress(投稿型)で公演日が本文内。要個別対応（URLは判明）。
    Venue("amatora",  "尼崎tora", "兵庫県", "todo", "https://live-tora.com", priority="A"),
    Venue("kobe108",  "KOBE108", "兵庫県", "todo", "", priority="B"),
    Venue("himejibeta", "姫路Beta", "兵庫県", "todo", "", priority="B"),
    Venue("chickengeorge", "CHICKEN GEORGE", "兵庫県", "todo", "", priority="C"),

    # ============================ 京都府 ============================
    Venue("growly",  "京都GROWLY", "京都府", "growly", "https://growly.net", verified=True, priority="A"),
    Venue("nano",    "Live House nano", "京都府", "nano", "https://livehouse-nano.com", verified=True, priority="A"),
    Venue("kyotomojo", "KYOTO MOJO", "京都府", "mojo", "https://kyoto-mojo.com", verified=True, priority="A"),
    Venue("dewey",   "木屋町DEWEY", "京都府", "dewey", "https://www.kiyamachi-dewey.com", verified=True, priority="A"),
    Venue("kyotomuse", "京都MUSE", "京都府", "musearm", "http://muse-live.com/kyoto", verified=True, priority="B"),
    # 磔磔: 本サイトは takutaku.jp。公演がHTMLコメント内でJS描画→Playwright要。
    Venue("takutaku", "磔磔", "京都府", "todo", "https://takutaku.jp", priority="B"),
    Venue("afterbeat", "AFTER BEAT", "京都府", "ical", "https://afterbeat.jp", verified=True, priority="B"),  # The Events Calendar iCal（出演者まで取得）
    Venue("otomakasu", "音まかす", "京都府", "todo", "", priority="B"),

    # ==================== 奈良・滋賀・和歌山 ====================
    Venue("neverland", "奈良NEVERLAND", "奈良県", "neverland", "https://nara-neverland.com", verified=True, priority="A"),
    # U★STONE: /live/ の公演がJS描画らしく静的HTMLに構造が出ない。別アプローチ要。
    Venue("ustone",  "U★STONE", "滋賀県", "todo", "https://u-stone.jp", priority="B"),
    Venue("bflat",   "B-FLAT", "滋賀県", "bflat", "http://www.livehouse-b-flat.jp", verified=True, priority="B"),
    Venue("clubgate", "CLUB GATE", "和歌山県", "clubgate", "https://club-gate.com", verified=True, priority="B"),  # My Calendar（出演者は空）
    Venue("oldtime", "OLDTIME", "和歌山県", "todo", "", priority="C"),
]

VENUES_BY_KEY = {v.key: v for v in VENUES}


def get_venues(
    keys: list[str] | None = None,
    only_verified: bool = False,
    priority: list[str] | None = None,
    include_todo: bool = False,
) -> list[Venue]:
    """会場を絞り込んで返す。

    keys を指定した場合はそのキーの会場だけを（todoでも）返す。
    keys 未指定なら、デフォルトでは未実装(todo)会場は除外する。
    """
    if keys:
        wanted = set(keys)
        return [v for v in VENUES if v.key in wanted]

    vs = VENUES
    if not include_todo:
        vs = [v for v in vs if v.scraper != "todo"]
    if only_verified:
        vs = [v for v in vs if v.verified]
    if priority:
        pr = set(priority)
        vs = [v for v in vs if v.priority in pr]
    return vs


def stats() -> dict:
    """登録状況の集計（実装済み / 未実装、都道府県別）。"""
    from collections import Counter
    impl = [v for v in VENUES if v.scraper != "todo"]
    todo = [v for v in VENUES if v.scraper == "todo"]
    return {
        "total": len(VENUES),
        "implemented": len(impl),
        "todo": len(todo),
        "by_pref": dict(Counter(v.prefecture for v in VENUES)),
        "todo_by_pref": dict(Counter(v.prefecture for v in todo)),
    }
