"""スクレイパー基底クラス"""
import time
import re
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from utils.logger import get_logger


class BaseScraper(ABC):
    """スクレイパーの基底クラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: 設定情報
        """
        self.config = config
        self.property_config = config['property']
        self.scraping_config = config['scraping']
        
        self.logger = get_logger(self.__class__.__name__)
        
        # セッションの設定
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.scraping_config['user_agent']
        })
    
    def _get_page(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        """
        ページを取得する
        
        Args:
            url: URL
            params: クエリパラメータ
        
        Returns:
            BeautifulSoup: パースされたHTML（失敗時はNone）
        """
        retries = self.scraping_config['max_retries']
        timeout = self.scraping_config['timeout']
        

        
        for attempt in range(retries):
            try:
                self.logger.info(f"Fetching: {url}")
                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                
                # エンコーディングの自動検出
                response.encoding = response.apparent_encoding
                
                return BeautifulSoup(response.text, 'lxml')
            
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # エクスポネンシャルバックオフ
                else:
                    self.logger.error(f"Failed to fetch {url}: {e}")
                    return None
        
        return None
    
    def _wait(self):
        """リクエスト間隔を空ける"""
        interval = self.scraping_config['request_interval']
        self.logger.debug(f"Waiting {interval} seconds...")
        time.sleep(interval)
    
    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する（サブクラスで実装）
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        データソース名を取得する（サブクラスで実装）
        
        Returns:
            str: データソース名
        """
        pass
    
    def _parse_price(self, price_str: str) -> Optional[int]:
        """
        価格文字列を数値に変換する
        
        Args:
            price_str: 価格文字列（例: "7,500万円", "1億6180万円"）
        
        Returns:
            int: 価格（円）、パース失敗時はNone
        """
        if not price_str:
            return None
        
        try:
            # 余分な括弧書きを除去（例: "2万3200円（委託(通勤)）" -> "2万3200円"）
            price_str = re.sub(r'（.*?）', '', price_str)
            price_str = re.sub(r'\(.*?\)', '', price_str)
            
            # カンマと空白を除去
            price_str = price_str.replace(',', '').replace(' ', '').replace('　', '')
            
            # "／月" などを除去
            price_str = price_str.replace('／月', '').replace('/月', '')
            
            # 億と万円が混在する場合（例: "1億6180万円")
            if '億' in price_str and '万円' in price_str:
                # "1億6180万円" -> ["1", "6180万円"]
                parts = price_str.split('億')
                oku_part = float(parts[0])
                man_part = float(parts[1].replace('万円', ''))
                return int(oku_part * 100000000 + man_part * 10000)
            
            # 万円の場合
            if '万円' in price_str:
                value = float(price_str.replace('万円', ''))
                return int(value * 10000)
            
            # 億円の場合
            if '億円' in price_str:
                value = float(price_str.replace('億円', ''))
                return int(value * 100000000)
            
            # 円の場合
            if '円' in price_str and '万' in price_str:
                # "2万3200円" -> 23200
                val = price_str.replace('円', '')
                parts = val.split('万')
                man = float(parts[0])
                rest = float(parts[1]) if parts[1] else 0
                return int(man * 10000 + rest)

            if '円' in price_str:
                return int(price_str.replace('円', ''))
            
            # 単位が取れて数値のみになっている場合
            if price_str.isdigit():
                return int(price_str)
            
            return None
        
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Failed to parse price: {price_str} - {e}")
            return None
    
    def _parse_area(self, area_str: str) -> Optional[float]:
        """
        面積文字列を数値に変換する
        
        Args:
            area_str: 面積文字列（例: "65.50m²", "58.02m2（17.55）（壁芯）"）
        
        Returns:
            float: 面積（m²）、パース失敗時はNone
        """
        if not area_str:
            return None
        
        try:
            # 数値の抽出（最初の数値を取得）
            import re
            match = re.search(r'([0-9]+\.?[0-9]*)', area_str)
            if match:
                return float(match.group(1))
            
            return None
        
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Failed to parse area: {area_str} - {e}")
            return None
    
    def _parse_floor(self, floor_str: str) -> Optional[int]:
        """
        階数文字列を数値に変換する
        
        Args:
            floor_str: 階数文字列（例: "15階"）
        
        Returns:
            int: 階数、パース失敗時はNone
        """
        if not floor_str:
            return None
        
        try:
            # 階を除去
            floor_str = floor_str.replace('階', '').replace(' ', '').replace('　', '')
            
            # 地下の場合
            if 'B' in floor_str or '地下' in floor_str:
                floor_str = floor_str.replace('B', '').replace('地下', '')
                return -int(floor_str)
            
            return int(floor_str)
        
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Failed to parse floor: {floor_str} - {e}")
            return None
