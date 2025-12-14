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
    logger.info("ブランズタワー豊洲 物件データ収集を開始します")
    logger.info("=" * 60)
    
    # 設定の読み込み
    try:
        config = load_config()
        logger.info(f"Target property: {config['property']['name']}")
        logger.info(f"Layouts: {', '.join(config['property']['layouts'])}")
    except FileNotFoundError:
        logger.error("Config file not found: config/config.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file: {e}")
        sys.exit(1)
    
    # データマネージャーの初期化
    data_manager = DataManager(config)
    
    # 全LDKタイプのデータを収集
    all_layouts_data = []
    
    for layout in config['property']['layouts']:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"間取り: {layout} のデータ収集を開始")
        logger.info(f"{'=' * 60}")
        
        # 現在のレイアウト用に設定を一時的に更新
        current_config = config.copy()
        current_config['property'] = config['property'].copy()
        current_config['property']['layout'] = layout
        
        # スクレイパーの初期化
        scrapers = [
            SuumoScraper(current_config),
            HomesScraper(current_config),
            AthomeScraper(current_config),
            RehouseScraper(current_config),
            LivableScraper(current_config),
        ]
        
        # 各サイトからデータを収集
        layout_data = []
        for scraper in scrapers:
            try:
                logger.info(f"\n--- {scraper.get_source_name()} からデータ収集を開始 ---")
                listings = scraper.scrape()
                
                if listings:
                    # 各物件にlayout情報を追加（まだ設定されていない場合のみ）
                    for listing in listings:
                        if 'layout' not in listing:
                            listing['layout'] = layout
                    
                    # 生データを保存
                    raw_file = data_manager.save_raw_data(
                        scraper.get_source_name().lower().replace(' ', '_'),
                        listings,
                        layout
                    )
                    logger.info(f"Raw data saved: {raw_file}")
                    
                    layout_data.append({
                        'source': scraper.get_source_name(),
                        'listings': listings
                    })
                else:
                    logger.warning(f"No data collected from {scraper.get_source_name()}")
            
            except Exception as e:
                logger.error(f"Error scraping {scraper.get_source_name()}: {e}", exc_info=True)
                continue
        
        # このLDKのデータを全体リストに追加
        all_layouts_data.extend(layout_data)
        
        logger.info(f"\n{layout} のデータ収集完了: {sum(len(d['listings']) for d in layout_data)}件")
    
    # データの統合
    if all_layouts_data:
        logger.info("\n" + "=" * 60)
        logger.info("全LDKのデータ統合処理を開始")
        logger.info("=" * 60)
        merged_listings = data_manager.merge_data(all_layouts_data)
        
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
        print(f"間取り: {', '.join(config['property']['layouts'])}")
        print(f"収集サイト数: {len(set(d['source'] for d in all_layouts_data))}サイト")
        print(f"総物件数: {len(merged_listings)}件")
        
        # LDK別の件数を表示
        print(f"\n間取り別の収集数:")
        layout_counts = {}
        for listing in merged_listings:
            layout = listing.get('layout', 'Unknown')
            layout_counts[layout] = layout_counts.get(layout, 0) + 1
        for layout in sorted(layout_counts.keys()):
            print(f"  - {layout}: {layout_counts[layout]}件")
        
        print(f"\nサイト別の収集数:")
        source_counts = {}
        for data in all_layouts_data:
            source = data['source']
            source_counts[source] = source_counts.get(source, 0) + len(data['listings'])
        for source in sorted(source_counts.keys()):
            print(f"  - {source}: {source_counts[source]}件")
            
        print(f"\n保存先: {processed_file}")
        print("=" * 60)
        
    else:
        logger.warning("No data collected from any source")
        print("\n⚠️  データが収集できませんでした")



if __name__ == '__main__':
    main()
