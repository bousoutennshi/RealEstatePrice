"""三井のリハウススクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup

class RehouseScraper(BaseScraper):
    """三井のリハウスから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://www.rehouse.co.jp"
    TARGET_URL = "https://www.rehouse.co.jp/mansionlibrary/ABM0163500/"
    
    def get_source_name(self) -> str:
        return "Rehouse"
    
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        listings = []
        target_layout = self.property_config['layout'] # e.g. "2LDK"
        
        # 三井のリハウスのマンションライブラリページを取得
        # configからURLを取得、なければデフォルト（豊洲）を使用
        target_url = self.property_config.get('rehouse_url', "https://www.rehouse.co.jp/mansionlibrary/ABM0163500/")
        
        soup = self._get_page(target_url)
        if not soup:
            self.logger.error("Failed to fetch Rehouse page")
            return listings
            
        # 物件リストのコンテナを取得
        # パターン1: マンションライブラリ (.mansion-detail-properties)
        container = soup.select_one('.mansion-detail-properties')
        items = []
        is_search_result = False

        if container:
            items = container.select('.mansion-list-card.property-card')
            self.logger.info(f"Found {len(items)} items (Library Mode)")
        else:
            # パターン2: 検索結果 (.property-index-card)
            items = soup.select('.property-index-card') 
            # もしかしたら li.property-item かもしれないので予備も
            if not items:
                items = soup.select('li.property-item')
            
            if items:
                is_search_result = True
                self.logger.info(f"Found {len(items)} items (Search Result Mode)")
            else:    
                self.logger.warning("No properties container found")
                return listings
        
        count = 0
        for item in items:
            listing = None
            if is_search_result:
                listing = self._parse_search_listing(item)
            else:
                listing = self._parse_listing(item)
                
            if listing:
                # 間取りフィルタリング
                # configのlayout ("2LDK") が含まれているか
                # 完全一致または含む場合OKとする
                layout = listing.get('layout', '')
                if target_layout in layout:
                    listings.append(listing)
                    count += 1
                else:
                    self.logger.debug(f"Skipping layout: {layout} (Target: {target_layout})")
        
        self.logger.info(f"Extracted {count} valid listings matching {target_layout}")
        
        # 詳細情報の取得
        for i, listing in enumerate(listings):
            if 'url' in listing:
                self.logger.info(f"Fetching details for {listing['title']} ({i+1}/{len(listings)})...")
                details = self._fetch_details(listing['url'])
                if details:
                    listing.update(details)
                self._wait()
                
        return listings
    
    def _fetch_details(self, url: str) -> Dict[str, Any]:
        """
        詳細ページから追加情報を取得する
        
        Args:
            url: 詳細ページのURL
            
        Returns:
            Dict: 追加情報（管理費、修繕積立金、築年数、方角など）
        """
        details = {}
        try:
            soup = self._get_page(url)
            if not soup:
                return details

            targets = {
                '管理費': 'management_fee',
                '積立金': 'repair_reserve',
                '修繕積立金': 'repair_reserve',
                '築年月': 'age_years',
                '向き': 'direction',
                'バルコニー': 'direction' # 「バルコニー向き」等の場合
            }
            
            headers = soup.select('td.table-header')
            for th in headers:
                header_text = th.get_text(strip=True)
                
                # ターゲット情報が含まれているかチェック
                for key, field in targets.items():
                    if key in header_text:
                        # 既に取得済みの場合はスキップ（例：バルコニーより向きを優先したい場合など）
                        if field == 'direction' and 'direction' in details and key == 'バルコニー':
                            continue
                            
                        val_td = th.find_next_sibling('td')
                        if val_td:
                            val_text = val_td.get_text(strip=True)
                            
                            if field == 'management_fee':
                                details['management_fee'] = self._parse_price(val_text)
                            elif field == 'repair_reserve':
                                details['repair_reserve'] = self._parse_price(val_text)
                            elif field == 'age_years':
                                # "2021年10月築" -> 築年数計算
                                match = re.search(r'(\d{4})年', val_text)
                                if match:
                                    year = int(match.group(1))
                                    current_year = 2025 # 仮定
                                    details['age_years'] = current_year - year
                            elif field == 'direction':
                                # "北西" など
                                details['direction'] = val_text
                                
        except Exception as e:
            self.logger.warning(f"Failed to fetch details from {url}: {e}")
            
        return details

    def _parse_listing(self, item: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        物件要素から情報を抽出する
        
        Args:
            item: BeautifulSoupの要素 (.mansion-list-card)
        
        Returns:
            Dict: 物件データ
        """
        try:
            data = {
                'source': self.get_source_name(),
            }
            
            # 詳細セクション
            desc_section = item.select_one('.description-section')
            if not desc_section:
                return None
                
            # タイトル
            title_el = desc_section.select_one('.property-title')
            if title_el:
                data['title'] = title_el.get_text(strip=True)
            else:
                data['title'] = "Unknown Title"
            
            # URL
            link = item.select_one('a.data-link')
            if link and link.get('href'):
                data['url'] = urljoin(self.BASE_URL, link.get('href'))
                
            # 価格
            price_el = desc_section.select_one('.price-text')
            if price_el:
                data['price'] = self._parse_price(price_el.get_text(strip=True))
                
            # スペック (間取り / 面積 / 階数)
            # <div class="content">1LDK / 43.41㎡ / 16階</div>
            content_el = desc_section.select_one('.content')
            if content_el:
                content_text = content_el.get_text(strip=True)
                parts = [p.strip() for p in content_text.split('/')]
                
                # フォーマットに柔軟に対応
                for part in parts:
                    if 'LDK' in part or 'DK' in part or 'K' in part or 'R' in part:
                         # 面積っぽくない、階っぽくないものを間取りとみなす簡易ロジック
                         if '㎡' not in part and '階' not in part:
                             data['layout'] = part
                    
                    if '㎡' in part or 'm2' in part:
                        data['area'] = self._parse_area(part)
                        
                    if '階' in part and 'm' not in part: # mを含まない階
                        data['floor'] = self._parse_floor(part)
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse Rehouse listing: {e}")
            return None
            
    def _parse_search_listing(self, item: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        検索結果ページ（.property-index-card）から情報を抽出する
        """
        try:
            data = {
                'source': self.get_source_name(),
            }
            
            # タイトル & URL
            # 通常 h2 または .object-name などのクラス
            title_el = item.select_one('.object-name, h2, .tit_bukken')
            link = item.select_one('a')
            
            if title_el:
                data['title'] = title_el.get_text(strip=True)
            else:
                # リンク内のテキストをタイトルとする
                data['title'] = link.get_text(strip=True) if link else "Unknown Title"
                
            if link and link.get('href'):
                data['url'] = urljoin(self.BASE_URL, link.get('href'))
                
            # 全テキストから価格・間取り等を抽出する
            text = item.get_text(separator=' ', strip=True)
            
            # 価格 (例: 1億2,800万円, "1 億 2,800 万円")
            price_match = re.search(r'((?:[\d,]+\s*億)?\s*(?:[\d,]+\s*)万円|[\d,]+\s*億円)', text)
            if price_match:
                data['price'] = self._parse_price(price_match.group(0))
            else:
                self.logger.warning(f"Price not found in text: {text[:50]}...")
                
            # 間取り (例: 3LDK)
            # 数字 + (LDK|DK|K|R) というパターン
            layout_match = re.search(r'(\d+[SLDKR]+)', text)
            if layout_match:
                data['layout'] = layout_match.group(1)
                
            # 面積 (例: 70.00㎡)
            area_match = re.search(r'([\d]+(?:\s*\.\s*[\d]+)?)\s*(㎡|m\s*2)', text)
            if area_match:
                data['area'] = self._parse_area(area_match.group(1))
                
            # 階数 (例: 20階)
            floor_match = re.search(r'(\d+)階', text)
            if floor_match:
                data['floor'] = self._parse_floor(floor_match.group(1))
                
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to parse Rehouse search listing: {e}")
            return None
