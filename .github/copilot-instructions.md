# GitHub Copilot Instructions

## プロジェクト概要
- 目的: ステータスが Failed となった systemd サービスを Discord に通知する
- 主な機能:
  - `systemctl` コマンドで Failed 状態のサービスを検知
  - Discord Bot API を使用して通知
  - Failed から復帰したサービスの通知
- 対象ユーザー: Linux サーバー管理者

## 共通ルール
- 会話は日本語で行う。
- PR とコミットは Conventional Commits に従う。
  - 形式: `<type>(<scope>): <description>`
  - `<description>` は日本語で記載
- 日本語と英数字の間には半角スペースを入れる。

## 技術スタック
- 言語: Python 3.x
- 依存ライブラリ: `python-dotenv`, `requests`
- ツール: `flake8`

## コーディング規約
- フォーマット: `flake8` のルールに従う
- 命名規則: Python の標準的な命名規則 (PEP 8 準拠)
- ドキュメント: 関数やクラスには日本語で docstring を記述する

## 開発コマンド
```bash
# 依存関係のインストール
pip install -U -r requirements.txt

# Lint (CI と同様の設定)
flake8 . --count --select=E1,E2,E3,E4,E7,E9,W1,W2,W3,W4,W5,F63,F7,F82 --show-source --statistics

# 実行 (ローカル)
python3 -m src
```

## テスト方針
- 現状、自動テストコード (`tests/` など) は存在しないため、動作確認は実機または手動で行う。

## セキュリティ / 機密情報
- `DISCORD_TOKEN` などの認証情報は `.env` ファイルで管理し、絶対にコミットしない。
- ログにトークンやチャンネル ID を出力しない。

## リポジトリ固有
- Systemd の状態に依存するため、Linux 環境 (Systemd 使用) での動作が前提。
- `SystemdFiles/` ディレクトリに systemd 用のユニットファイルが含まれている。
