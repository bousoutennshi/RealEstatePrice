"""at homeスクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper


class AthomeScraper(BaseScraper):
    """at homeから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://www.athome.co.jp"
    
    def get_source_name(self) -> str:
        return "at_home"
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        property_name = self.property_config['name']
        layout = self.property_config['layout']
        
        self.logger.info(f"Note: at home scraper requires manual URL setup")
        self.logger.info(f"Please visit at home website and search for '{property_name} {layout}'")
        
        listings = []
        
        return listings
    
    def _parse_listing(self, listing_elem) -> Optional[Dict[str, Any]]:
        """
        物件要素から情報を抽出する
        
        Args:
            listing_elem: BeautifulSoupの要素
        
        Returns:
            Dict: 物件データ
        """
        try:
            data = {
                'source': self.get_source_name(),
            }
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse listing: {e}")
            return None
