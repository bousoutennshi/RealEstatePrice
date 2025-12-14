"""at homeスクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper


class AthomeScraper(BaseScraper):
    """at homeから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://www.athome.co.jp"
    
    def get_source_name(self) -> str:
        return "at home"
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        property_name = self.property_config['name']
        layout = self.property_config['layout']
        
        # 間取りからat homeのkmパラメータを取得
        # km005=1K, km006=1DK, km007=1LDK, km010=2LDK, km015=3LDK, km020=4LDK
        layout_map = {
            '1K': 'km005',
            '1DK': 'km006',
            '1LDK': 'km007',
            '2K': 'km010',  # 正確なコードは不明ですが、2LDKと同様に扱います
            '2DK': 'km010',
            '2LDK': 'km010',
            '3K': 'km015',
            '3DK': 'km015',
            '3LDK': 'km015',
            '4K': 'km020',
            '4DK': 'km020',
            '4LDK': 'km020',
        }
        
        km_value = layout_map.get(layout, 'km010')  # デフォルトは2LDK
        
        # at homeの検索URL
        url = "https://www.athome.co.jp/mansion/chuko/tokyo/toyosu-st/list/"
        params = {
            'pref': '13',
            'stations': 'tokyometroyurakucho_2347-2347220',
            'basic': f'kp120,kp001,{km_value},kt101,ke001,kn001,kj001',
            'freeword': property_name,
            'q': '1',
            'sort': '95',
            'limit': '100'
        }
        
        soup = self._get_page(url, params)
        if not soup:
            return []
        
        listings = []
        
        # 物件リストを取得（<a href="/mansion/数字..." target="_blank">）
        listing_elems = soup.select('a[href^="/mansion/"][target="_blank"]')
        self.logger.info(f"Found {len(listing_elems)} listings")
        
        for listing_elem in listing_elems:
            data = self._parse_listing(listing_elem)
            if data:
                listings.append(data)
                self.logger.info(f"Parsed: {data.get('title')} - {data.get('price')}円")
        
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
            
            # URL
            href = listing_elem.get('href')
            if href:
                data['url'] = urljoin(self.BASE_URL, href)
            
            # タイトル（例: "ブランズタワー豊洲 14階 ２ＬＤＫ"）
            title_elem = listing_elem.select_one('.title-wrap__title-text')
            if title_elem:
                title_text = title_elem.get_text(strip=True)
                data['title'] = title_text
                
                # タイトルから階数と間取りを抽出
                # 例: "ブランズタワー豊洲 14階 ２ＬＤＫ"
                floor_match = re.search(r'(\d+)階', title_text)
                if floor_match:
                    data['floor'] = int(floor_match.group(1))
                
                # 全角・半角両対応（１２３４ and 1234、ＬＤＫ and LDK）
                layout_match = re.search(r'([１２３４1-4][ＬL][ＤD][ＫK]|[１２３４1-4][ＤD][ＫK]|[１２３４1-4][ＫK]|[１２３４1-4]R)', title_text)
                if layout_match:
                    layout_raw = layout_match.group(1)
                    # 全角を半角に変換
                    layout_normalized = layout_raw.translate(str.maketrans('１２３４ＬＤＫR', '1234LDKR'))
                    data['layout'] = layout_normalized

            
            # 価格
            price_elem = listing_elem.select_one('.property-price')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                data['price'] = self._parse_price(price_text)
            
            # 詳細テーブル（専有面積、築年月など）
            detail_table = listing_elem.select_one('.property-detail-table')
            if detail_table:
                # すべての strong (ラベル) と span (値) のペアを取得
                labels = detail_table.select('strong')
                values = detail_table.select('span')
                
                for label, value in zip(labels, values):
                    label_text = label.get_text(strip=True)
                    value_text = value.get_text(strip=True)
                    
                    # 専有面積
                    if '専有面積' in label_text:
                        data['area'] = self._parse_area(value_text)
                    
                    # 築年月（築年数を計算）
                    elif '築年月' in label_text:
                        # 築年月から築年数を計算
                        # 形式: "2020年3月" または "2020/3" など
                        year_match = re.search(r'(\d{4})', value_text)
                        if year_match:
                            built_year = int(year_match.group(1))
                            from datetime import datetime
                            current_year = datetime.now().year
                            data['age_years'] = current_year - built_year
            
            # 必須フィールドのチェック
            if 'price' not in data or 'title' not in data:
                self.logger.warning("Missing required fields in listing")
                return None
            
            # 物件名フィルタリング
            # タイトルに設定された物件名が含まれているか確認
            property_name = self.property_config.get('name', '')
            if property_name and property_name not in data.get('title', ''):
                self.logger.debug(f"Skipping listing: '{data.get('title')}' does not match property name '{property_name}'")
                return None
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse listing: {e}")
            return None

