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
        soup = self._get_page(self.TARGET_URL)
        if not soup:
            self.logger.error("Failed to fetch Rehouse page")
            return listings
            
        # 物件リストのコンテナを取得
        # 解析結果: .mansion-detail-properties 内の .mansion-list-card
        container = soup.select_one('.mansion-detail-properties')
        if not container:
            self.logger.warning("No properties container found")
            return listings
            
        items = container.select('.mansion-list-card.property-card')
        self.logger.info(f"Found {len(items)} items on Rehouse page")
        
        count = 0
        for item in items:
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
