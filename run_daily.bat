@echo off
REM ============================================================
REM  GAGA Kansai Artist Radar - 日次実行バッチ
REM  Windowsタスクスケジューラからこのファイルを実行する。
REM  ・作業フォルダに移動し、venvのpythonで daily.py を実行
REM  ・出力は output\logs\daily_YYYYMMDD_HHMMSS.log に保存
REM  ・Sheets連携する場合は下の行に --sheets を付ける（credentials.json必須）
REM ============================================================
cd /d "%~dp0"

if not exist "output\logs" mkdir "output\logs"

REM ロケール非依存のタイムスタンプ（PowerShellで生成）
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
set LOG=output\logs\daily_%TS%.log

echo [%TS%] daily start >> "%LOG%"
REM --- Sheets運用（データ本体はGoogle Sheets、ローカルCSVは作らない） ---
".venv\Scripts\python.exe" daily.py --sheets-only >> "%LOG%" 2>&1
echo [%TS%] daily end (exit=%errorlevel%) >> "%LOG%"

REM 参考: 運用モードを変えたい場合は上の行を差し替える
REM   ローカルCSVのみ         : daily.py
REM   ローカルCSV + Sheets両方 : daily.py --sheets
REM   Sheetsのみ（推奨・現行） : daily.py --sheets-only
