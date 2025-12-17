# 不動産物件価格データ収集システム

複数の不動産サイトから指定したマンションの物件情報を自動収集し、一元管理・可視化するシステムです。
GitHub Actionsを利用して毎日自動で最新データを収集・蓄積します。

## 🌐 稼働サイト

実際の稼働画面はこちら：
👉 **[https://realestateprice-production-3049.up.railway.app/](https://realestateprice-production-3049.up.railway.app/)**

## 📋 機能

### 収集データ
- 価格 / 坪単価
- 面積（m²）
- 階数 / 方角
- 管理費 / 修繕積立金
- 築年数
- データソース（掲載サイト）

### 対応サイト（実装済み）
- ✅ SUUMO（スーモ）
- ✅ HOME'S（ライフルホームズ）
- ✅ at home（アットホーム）
- ✅ 三井のリハウス
- ✅ 東急リバブル

### 主な特徴
- **複数物件対応**: 設定ファイルで複数の監視対象マンションを登録可能
- **全間取り対応**: 1LDK〜4LDKなど、任意の間取りタイプを収集対象に設定可能
- **自動更新**: GitHub Actionsにより毎日定期的に（JST 9:00頃）データを更新
- **重複排除**: 複数サイトに掲載されている同一物件を自動的に名寄せ
- **レスポンシブWeb UI**: PC・スマホ両対応のモダンな管理画面

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/RealEstatePrice.git
cd RealEstatePrice
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 設定ファイルの編集

`config/config.json` を編集して、収集したい物件情報を設定します。

```json
{
  "properties": [
    {
      "id": "SampleTower",
      "name": "サンプルタワーレジデンス",
      "area": "東京都港区",
      "layouts": [
        "1LDK",
        "2LDK",
        "3LDK"
      ]
    }
  ],
  "scraping": {
    "request_interval": 3,
    "timeout": 10,
    "user_agent": "Mozilla/5.0 ...",
    "max_retries": 3
  },
  "output": {
    "data_base_dir": "data"
  }
}
```

## 💻 使用方法

### データの更新（手動実行）

```bash
python main.py
```

実行が完了すると `data/{PropertyID}/processed/latest.json` にデータが保存されます。

### Webサーバーの起動

収集したデータを閲覧するためのWebサーバーを起動します。

```bash
python server.py
```

ブラウザで `http://localhost:8000` にアクセスしてください。

## 🔄 自動更新（GitHub Actions）

本リポジトリにはGitHub Actionsのワークフローが含まれており、以下のスケジュールで自動実行されます。

- **実行時刻**: 毎日 日本時間 午前9時頃（設定は遅延を見越してUTC 22:00 = JST 7:00）
- **処理内容**:
  1. 全スクレイパーを実行して最新データを収集
  2. データに変更があれば自動的にコミット＆プッシュ
  3. RailwayなどのPaaSと連携していれば、自動デプロイでWebサイトも更新

## 📁 プロジェクト構造

```
RealEstatePrice/
├── .github/workflows/   # GitHub Actions設定
├── config/              # 設定ファイル
├── data/                # データ保存先（物件ごとに分割）
├── logs/                # ログファイル
├── scrapers/            # 各サイト用スクレイパー
├── web/                 # Webフロントエンド（HTML/CSS/JS）
├── main.py              # データ収集用メインスクリプト
├── server.py            # Web表示用APIサーバー
└── requirements.txt     # 依存ライブラリ
```

## 📄 ライセンス

個人使用のみ。商用利用不可。
各不動産サイトの利用規約を遵守してご利用ください。
