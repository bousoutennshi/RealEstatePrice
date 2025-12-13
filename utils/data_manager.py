"""データ管理ユーティリティ"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from utils.logger import get_logger


logger = get_logger(__name__)


class DataManager:
    """データの保存と管理を行うクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定情報
        """
        self.raw_data_dir = config['output']['raw_data_dir']
        self.processed_data_dir = config['output']['processed_data_dir']
        
        # ディレクトリの作成
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.processed_data_dir, exist_ok=True)
    
    def save_raw_data(self, source: str, data: List[Dict[str, Any]]) -> str:
        """
        生データを保存する（固定ファイル名で上書き）
        
        Args:
            source: データソース名（例: "suumo"）
            data: 物件データのリスト
        
        Returns:
            str: 保存したファイルパス
        """
        filename = f"{source}_latest.json"
        filepath = os.path.join(self.raw_data_dir, filename)
        
        output_data = {
            'source': source,
            'timestamp': datetime.now().isoformat(),
            'count': len(data),
            'listings': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Raw data saved: {filepath} ({len(data)} listings)")
        return filepath
    
    def load_raw_data(self, filepath: str) -> Dict[str, Any]:
        """
        生データを読み込む
        
        Args:
            filepath: ファイルパス
        
        Returns:
            Dict: データ
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def merge_data(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        複数のデータソースからのデータをマージし、重複を排除する
        
        Args:
            data_list: データのリスト
        
        Returns:
            List: マージされたデータ
        """
        all_listings = []
        seen_urls = set()
        
        for data in data_list:
            for listing in data.get('listings', []):
                url = listing.get('url')
                # URLで重複チェック
                if url and url not in seen_urls:
                    all_listings.append(listing)
                    seen_urls.add(url)
                elif not url:
                    # URLがない場合は追加（重複チェック不可）
                    all_listings.append(listing)
        
        logger.info(f"Merged data: {len(all_listings)} unique listings from {len(data_list)} sources")
        return all_listings
    
    def save_processed_data(self, data: List[Dict[str, Any]], property_name: str) -> str:
        """
        処理済みデータを保存する（固定ファイル名で上書き）
        
        Args:
            data: 統合された物件データのリスト
            property_name: 物件名
        
        Returns:
            str: 保存したファイルパス
        """
        filename = "latest.json"
        filepath = os.path.join(self.processed_data_dir, filename)
        
        output_data = {
            'property_name': property_name,
            'last_updated': datetime.now().isoformat(),
            'total_listings': len(data),
            'listings': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Processed data saved: {filepath} ({len(data)} listings)")
        return filepath
    
    def get_latest_processed_file(self) -> str:
        """
        最新の処理済みファイルを取得する
        
        Returns:
            str: ファイルパス（存在しない場合はNone）
        """
        filepath = os.path.join(self.processed_data_dir, "latest.json")
        if os.path.exists(filepath):
            return filepath
        return None
