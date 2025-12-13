"""
ブランズタワー豊洲 2LDK物件データ収集メインスクリプト

複数の不動産サイトから物件情報を収集し、JSON形式で保存します。
"""
import json
import sys
from pathlib import Path
from datetime import datetime

from utils import setup_logger, DataManager
from scrapers import SuumoScraper, HomesScraper, AthomeScraper, RehouseScraper, LivableScraper


def load_config(config_path: str = 'config/config.json') -> dict:
    """
    設定ファイルを読み込む
    
    Args:
        config_path: 設定ファイルのパス
    
    Returns:
        dict: 設定情報
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """メイン処理"""
    # ロガーのセットアップ
    logger = setup_logger('main', 'logs/scraping.log')
    logger.info("=" * 60)
    logger.info("ブランズタワー豊洲 2LDK物件データ収集を開始します")
    logger.info("=" * 60)
    
    # 設定の読み込み
    try:
        config = load_config()
        logger.info(f"Target property: {config['property']['name']}")
        logger.info(f"Layout: {config['property']['layout']}")
    except FileNotFoundError:
        logger.error("Config file not found: config/config.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file: {e}")
        sys.exit(1)
    
    # データマネージャーの初期化
    data_manager = DataManager(config)
    
    # スクレイパーの初期化
    scrapers = [
        SuumoScraper(config),
        HomesScraper(config),
        AthomeScraper(config),
        RehouseScraper(config),
        LivableScraper(config),
    ]
    
    # 各サイトからデータを収集
    all_data = []
    for scraper in scrapers:
        try:
            logger.info(f"\n--- {scraper.get_source_name()} からデータ収集を開始 ---")
            listings = scraper.scrape()
            
            if listings:
                # 生データを保存
                raw_file = data_manager.save_raw_data(
                    scraper.get_source_name().lower().replace(' ', '_'),
                    listings
                )
                logger.info(f"Raw data saved: {raw_file}")
                
                all_data.append({
                    'source': scraper.get_source_name(),
                    'listings': listings
                })
            else:
                logger.warning(f"No data collected from {scraper.get_source_name()}")
        
        except Exception as e:
            logger.error(f"Error scraping {scraper.get_source_name()}: {e}", exc_info=True)
            continue
    
    # データの統合
    if all_data:
        logger.info("\n--- データの統合処理を開始 ---")
        merged_listings = data_manager.merge_data(all_data)
        
        # 統合データを保存
        processed_file = data_manager.save_processed_data(
            merged_listings,
            config['property']['name']
        )
        
        logger.info("=" * 60)
        logger.info("データ収集が完了しました")
        logger.info(f"総物件数: {len(merged_listings)}件")
        logger.info(f"保存先: {processed_file}")
        logger.info("=" * 60)
        
        # サマリー表示
        print("\n" + "=" * 60)
        print("📊 データ収集結果サマリー")
        print("=" * 60)
        print(f"物件名: {config['property']['name']}")
        print(f"間取り: {config['property']['layout']}")
        print(f"収集サイト数: {len(all_data)}サイト")
        print(f"総物件数: {len(merged_listings)}件")
        print(f"\n各サイトからの収集数:")
        for data in all_data:
            print(f"  - {data['source']}: {len(data['listings'])}件")
        print(f"\n保存先: {processed_file}")
        print("=" * 60)
        
    else:
        logger.warning("No data collected from any source")
        print("\n⚠️  データが収集できませんでした")


if __name__ == '__main__':
    main()
