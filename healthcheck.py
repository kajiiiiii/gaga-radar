# -*- coding: utf-8 -*-
"""稼働中スクレイパの健全性チェック。

各会場について指定月（既定=今月）を取得し、件数を一覧表示。
0件の会場は「サイト改装などでパーサが壊れた可能性」として警告する。
日次運用の監視用。詳細ページは取得しない（速く・軽く）。

使い方:
  python healthcheck.py            # 今月
  python healthcheck.py 2026 10    # 指定年月
"""
from __future__ import annotations

import sys
from datetime import date

import config
config.FETCH_DETAILS = False  # 件数確認だけなので詳細は取らない（軽量化）

from scrapers import get_scraper   # noqa: E402
from venues import get_venues      # noqa: E402


def main() -> int:
    if len(sys.argv) >= 3:
        year, month = int(sys.argv[1]), int(sys.argv[2])
    else:
        t = date.today()
        year, month = t.year, t.month

    venues = get_venues()  # 実装済みのみ
    print(f"=== healthcheck {year}/{month:02d}  対象 {len(venues)} 会場 ===\n")

    total = 0
    zero: list[str] = []
    errors: list[str] = []
    for v in venues:
        try:
            n = len(get_scraper(v).scrape_month(year, month))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{v.name}: {e}")
            print(f"  [ERR ] {v.name:24} {e}")
            continue
        total += n
        mark = "  " if n > 0 else "!!"
        print(f"  [{mark}] {v.name:24} {n:5} 件")
        if n == 0:
            zero.append(v.name)

    print(f"\n合計 {total} 件 / {len(venues)} 会場")
    if zero:
        print(f"⚠ 0件の会場（要確認）: {', '.join(zero)}")
    if errors:
        print(f"⚠ エラー: {len(errors)} 件")
    # 0件・エラーが無ければ正常終了(0)、あれば1
    return 0 if not (zero or errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())
