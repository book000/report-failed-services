# GEMINI.md

## 目的
このドキュメントは、Gemini CLI が `report-failed-services` リポジトリで作業を行う際のコンテキストと方針を定義します。

## 出力スタイル
- **言語**: 日本語 (ユーザーへの回答、説明)
- **トーン**: 丁寧かつ簡潔に
- **形式**: Markdown

## 共通ルール
- **会話言語**: 日本語
- **コミット規約**: Conventional Commits (`<type>(<scope>): <description>`)、description は日本語
- **表記**: 日本語と英数字の間に半角スペースを入れる

## プロジェクト概要
- **目的**: Systemd の Failed サービス検知・Discord 通知
- **主要技術**: Python 3.x, Systemd (`systemctl`), Discord Webhook

## コーディング規約
- **フォーマット**: `flake8` 準拠
- **命名**: PEP 8 (Python 標準)
- **コメント**: 日本語
- **エラーメッセージ**: 英語

## 開発コマンド
```bash
# 依存関係インストール
pip install -U -r requirements.txt

# Lint チェック
flake8 . --count --select=E1,E2,E3,E4,E7,E9,W1,W2,W3,W4,W5,F63,F7,F82 --show-source --statistics

# 実行
python3 -m src
```

## 注意事項
- **セキュリティ**: `.env` ファイルやコード内にトークンを埋め込んでコミットしないこと。
- **安全性**: Systemd コマンドを実行するツールであるため、システムへの影響を考慮すること。
- **既存ルール**: プロジェクトに既存の `.gitignore` や `flake8` 設定がある場合はそれを優先する。

## リポジトリ固有
- 実行には `Systemd` が稼働している Linux 環境が必要。
- `SystemdFiles/` にはインストーラーとユニットファイルが含まれる。
