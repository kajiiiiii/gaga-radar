# -*- coding: utf-8 -*-
"""
Google Sheets 接続の段階診断ツール。

セットアップの各段階でこれを実行すると、「今どこまでできていて、次に何をすべきか」を
教えてくれる。エラーで止めず、次の一手を日本語で案内する。

使い方:
  python check_sheets.py
"""
from __future__ import annotations

import json
import sys

import config

LINE = "-" * 60


def fail(msg: str, nexts: list[str]) -> int:
    print(f"\n❌ {msg}")
    print("→ 次にやること:")
    for s in nexts:
        print(f"   ・{s}")
    return 1


def main() -> int:
    print(LINE)
    print("Google Sheets 接続チェック")
    print(LINE)

    cred = config.GOOGLE_CREDENTIALS_FILE

    # --- 段階1: credentials.json があるか ---
    if not cred.exists():
        return fail(
            f"認証キー {cred} が見つかりません。",
            [
                "Google Cloud Console でプロジェクト作成",
                "「Google Sheets API」と「Google Drive API」を有効化",
                "サービスアカウントを作成 → 鍵(JSON)を作成してダウンロード",
                f"そのJSONを {cred} という名前で置く",
                "もう一度 python check_sheets.py を実行",
            ],
        )
    print(f"✅ 認証キー: {cred}")

    # --- 段階2: JSONが読めて、共有先メールが分かるか ---
    try:
        info = json.loads(cred.read_text(encoding="utf-8"))
        sa_email = info.get("client_email", "")
        project = info.get("project_id", "")
    except Exception as e:  # noqa: BLE001
        return fail(f"認証キーのJSONが壊れています: {e}",
                    ["ダウンロードし直して置き換える"])
    if not sa_email:
        return fail("JSONに client_email がありません（サービスアカウント鍵ではない可能性）。",
                    ["サービスアカウントの『鍵』から作成したJSONか確認する"])
    print(f"✅ サービスアカウント: {sa_email}")
    print(f"   （プロジェクト: {project}）")
    print(f"\n★ このメールアドレスに、スプレッドシートを『編集者』で共有してください:\n   {sa_email}\n")

    # --- 段階3: gspread で認証できるか ---
    try:
        import gspread  # noqa: PLC0415
    except ImportError:
        return fail("gspread が未インストールです。",
                    ["pip install -r requirements.txt を実行"])
    try:
        gc = gspread.service_account(filename=str(cred))
    except Exception as e:  # noqa: BLE001
        return fail(f"認証に失敗しました: {e}",
                    ["鍵JSONが正しいか、時計がズレていないか確認"])
    print("✅ 認証OK")

    # --- 段階4: 対象スプレッドシートを開けるか ---
    name = config.SPREADSHEET_NAME
    try:
        sh = gc.open(name)
    except gspread.SpreadsheetNotFound:
        return fail(
            f"スプレッドシート「{name}」が見つからない/共有されていません。",
            [
                f"Googleスプレッドシートを新規作成し、名前を「{name}」にする",
                f"右上『共有』で {sa_email} を『編集者』に追加",
                "python check_sheets.py を再実行",
            ],
        )
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        nexts = ["エラーメッセージを確認"]
        if "PERMISSION_DENIED" in msg or "has not been used" in msg or "disabled" in msg:
            nexts = ["Google Sheets API と Google Drive API が『有効』か確認",
                     "有効化直後は数分待ってから再実行"]
        return fail(f"スプレッドシートを開けません: {msg}", nexts)
    print(f"✅ スプレッドシート「{name}」を開けました  ({sh.url})")

    # --- 段階5: 書き込みテスト ---
    try:
        ws = sh.sheet1
        ws.update_acell("Z1", "gaga-radar 接続テストOK")
        ws.update_acell("Z1", "")  # 後始末
    except Exception as e:  # noqa: BLE001
        return fail(f"書き込みできません（閲覧者のみ共有かも）: {e}",
                    [f"{sa_email} を『編集者』に変更する"])
    print("✅ 書き込みテストOK")

    print(f"\n{LINE}")
    print("🎉 すべてOK。次のコマンドでSheetsへ投入できます:")
    print("   python backfill.py --sheets      （まず一括投入）")
    print("   python daily.py --sheets-only    （以降の日次・Sheetsのみ運用）")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
