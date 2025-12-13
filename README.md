# ブランズタワー豊洲 2LDK物件データ収集システム

複数の不動産サイトから「ブランズタワー豊洲」の2LDK物件情報を自動収集するスクレイピングシステムです。

## 📋 機能

### 収集データ
- 価格
- 面積（m²）
- 階数
- 築年数
- 管理費
- 修繕積立金
- 方角
- 掲載日
- 物件URL
- データソース

### 対応サイト
- ✅ **SUUMO（スーモ）** - 実装済み
- ⏳ **HOME'S（ライフルホームズ）** - 実装予定
- ⏳ **at home** - 実装予定
- ⏳ **不動産ジャパン** - 実装予定

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
cd /path/to/RealEstatePrice
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの確認

`config/config.json` を確認・編集します。

```json
{
  "property": {
    "name": "ブランズタワー豊洲",
    "area": "東京都江東区豊洲",
    "layout": "2LDK"
  },
  "scraping": {
    "request_interval": 2,
    "timeout": 10,
    "user_agent": "...",
    "max_retries": 3
  }
}
```

## 💻 使用方法

本システムは、以下の2ステップで使用します。

### 1. データの更新（スクレイピング実行）

最新の物件情報を収集するには、以下のコマンドを実行します。これにより新しいJSONファイルが作成されます。

```bash
# 仮想環境の有効化（未実施の場合）
source venv/bin/activate

# スクレイピングの実行
python main.py
```

実行が完了すると、`data/processed/` ディレクトリに `latest.json` ファイルが生成されます。

> **注意:** データファイルは常に `latest.json` という固定ファイル名で上書き保存されます。過去のデータを保持したい場合は、実行前に手動でバックアップしてください。

### 2. Webサイトでの確認

収集したデータをリッチなインターフェースで確認するには、Webサーバーを起動します。

```bash
# Webサーバーの起動
python server.py
```

サーバー起動後、ブラウザで以下のURLにアクセスしてください：

👉 **http://localhost:8000**

Webサイトでは以下の機能が利用できます：
- **一覧表示**: 最新の収集データをカード形式で表示
- **詳細情報**: 価格、面積、階数、方角などを確認可能
- **ソート**: 価格順、面積順、階数順などで並べ替え
- **検索**: 物件名や説明文でリアルタイムフィルタリング
- **重複排除**: 条件が一致する物件を自動的にまとめて表示（「Unique Listings」）

**データの更新反映について**:
Webサイトは、リロードするたびに `latest.json` を読み込みます。データを更新したい場合は、ターミナルで `python main.py` を実行した後、ブラウザをリロードしてください。

### データの確認（コマンドライン）

統合済みデータ（`processed/merged_*.json`）の形式：

```json
{
  "property_name": "ブランズタワー豊洲",
  "last_updated": "2025-12-13T00:16:00+09:00",
  "total_listings": 15,
  "listings": [
    {
      "source": "SUUMO",
      "title": "ブランズタワー豊洲",
      "price": 75000000,
      "area": 65.5,
      "layout": "2LDK",
      "floor": 15,
      "age_years": 10,
      "management_fee": 15000,
      "repair_reserve": 8000,
      "direction": "南東",
      "posted_date": "2025-12-10",
      "url": "https://suumo.jp/..."
    }
  ]
}
```

**ファイル命名規則:**
- 統合データ: `data/processed/latest.json` (常に最新データで上書き)
- 生データ: `data/raw/{source}_latest.json` (各ソースごとに上書き)

## 📁 プロジェクト構造

```
RealEstatePrice/
├── README.md                    # このファイル
├── requirements.txt             # 依存ライブラリ
├── .gitignore                   # Git除外設定
├── main.py                      # メインスクリプト
├── config/
│   └── config.json             # 設定ファイル
├── scrapers/                    # スクレイパーモジュール
│   ├── __init__.py
│   ├── base_scraper.py         # 基底クラス
│   ├── suumo_scraper.py        # SUUMOスクレイパー
│   ├── homes_scraper.py        # HOME'Sスクレイパー
│   ├── athome_scraper.py       # at homeスクレイパー
│   └── fudosan_scraper.py      # 不動産ジャパンスクレイパー
├── utils/                       # ユーティリティモジュール
│   ├── __init__.py
│   ├── data_manager.py         # データ管理
│   └── logger.py               # ログ管理
├── data/                        # データ保存先
│   ├── raw/                    # 各サイトの生データ
│   └── processed/              # 統合済みデータ
└── logs/                        # ログファイル
```

## ⚙️ カスタマイズ

### 検索条件の変更

`config/config.json` を編集して、物件名や間取りを変更できます。

### リクエスト間隔の調整

サーバーへの負荷を考慮し、`request_interval`（秒）を調整してください。

```json
{
  "scraping": {
    "request_interval": 3  // 3秒に変更
  }
}
```

## ⚠️ 注意事項

### 法的遵守

- 各サイトの利用規約を遵守してください
- 個人的な使用に限定してください
- 過度なアクセスは避けてください

### サイト構造の変更

不動産サイトのHTML構造は頻繁に変更される可能性があります。スクレイパーが動作しなくなった場合は、該当ファイルのセレクターを更新してください。

### IP制限

頻繁なアクセスによりIPアドレスが一時的にブロックされる可能性があります。実行頻度に注意してください。

## 🚀 Railway デプロイ

Railway環境でWebサーバーをデプロイする際の注意事項：

### データの永続化

- Railway環境では、デプロイのたびにコンテナがリセットされます
- データを永続化する場合は、Railway Volumesの設定が必要です
- 本システムは `latest.json` という固定ファイルを使用するため、永続化設定がシンプルです

### 推奨デプロイ方法

1. **ローカルでスクレイピング実行**
   ```bash
   python main.py
   ```

2. **データファイルをコミット（オプション）**
   ```bash
   git add data/processed/latest.json
   git commit -m "Update property data"
   git push
   ```

3. **Railwayで自動デプロイ**
   - GitHubにpushすると自動的にRailwayでデプロイ
   - `server.py` がWebサーバーとして起動

### 環境変数設定（Railway）

```bash
PORT=8000  # Railwayが自動設定
```

## 🐛 トラブルシューティング

### データが取得できない

1. **サイトの構造変更を確認**
   - 各スクレイパーファイルのCSSセレクターを確認・更新

2. **ネットワーク接続を確認**
   - インターネット接続を確認
   - ファイアウォール設定を確認

3. **ログファイルを確認**
   - `logs/scraping.log` でエラー内容を確認

### 依存関係のインストールエラー

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 📝 ログ

実行ログは `logs/scraping.log` に保存されます。

## 🔄 今後の拡張予定

- [ ] HOME'Sスクレイパーの完全実装
- [ ] at homeスクレイパーの完全実装
- [ ] 不動産ジャパンスクレイパーの完全実装
- [ ] データの可視化機能
- [ ] 定期実行機能（cron対応）
- [ ] メール通知機能
- [ ] 価格推移の追跡機能

## 📄 ライセンス

個人使用のみ。商用利用不可。

## 👤 作成者

開発日: 2025年12月
