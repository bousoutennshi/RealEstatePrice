"""SUUMOスクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper


class SuumoScraper(BaseScraper):
    """SUUMOから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://suumo.jp"
    
    def get_source_name(self) -> str:
        return "SUUMO"
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        property_name = self.property_config['name']
        layout = self.property_config['layout']
        
        listings = self._search_listings(property_name, layout)
        
        self.logger.info(f"Found {len(listings)} listings from {self.get_source_name()}")
        return listings
    
    def _search_listings(self, property_name: str, layout: str) -> List[Dict[str, Any]]:
        """
        物件リストを検索する
        
        Args:
            property_name: 物件名
            layout: 間取り
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        listings = []
        
        # 間取りからSUUMOのmdパラメータを取得
        layout_map = {
            '1K': '1',
            '1DK': '1',
            '1LDK': '1',
            '2K': '2',
            '2DK': '2',
            '2LDK': '2',
            '3K': '3',
            '3DK': '3',
            '3LDK': '3',
            '4K': '4',
            '4DK': '4',
            '4LDK': '4',
        }
        
        # layoutから数字部分を抽出（例: "2LDK" -> "2"）
        md_value = layout_map.get(layout, '2')  # デフォルトは2LDK
        
        # SUUMOの検索URL
        search_url = "https://suumo.jp/jj/bukken/ichiran/JJ012FC001/"
        search_params = {
            'ar': '030',  # 関東
            'bs': '011',  # 中古マンション
            'fw': property_name,  # フリーワード
            'md': md_value,  # 間取り（動的に設定）
            'kb': '1',
            'kt': '9999999',
            'mb': '0',
            'mt': '9999999',
            'cn': '9999999',
            'et': '9999999',
        }
        
        page = 1
        while True:
            self.logger.info(f"Fetching page {page}...")
            
            # ページ番号の追加
            if page > 1:
                search_params['page'] = str(page)
            
            soup = self._get_page(search_url, params=search_params)
            if not soup:
                break
            
            # 物件リストの取得
            property_items = soup.select('.property_unit')
            if not property_items:
                self.logger.info("No more listings found")
                break
            
            self.logger.info(f"Found {len(property_items)} items on page {page}")
            
            # 各物件の情報を抽出
            for item in property_items:
                listing = self._parse_listing(item)
                if listing:
                    # 物件名のフィルタリング
                    # タイトルまたは物件全体のテキストから物件名をチェック
                    item_text = item.get_text(separator=' ', strip=True)
                    
                    # タイトルに物件名が含まれているか、または物件情報に物件名が含まれているかをチェック
                    if (property_name in listing.get('title', '') or 
                        f'物件名{property_name}' in item_text.replace(' ', '') or
                        property_name in item_text):
                        listings.append(listing)
                    else:
                        self.logger.debug(f"Skipped: {listing.get('title', 'No title')[:50]} (not {property_name})")
            
            # 次のページがあるかチェック
            next_page = soup.select_one('.pagination-parts li.pagination-parts--next a')
            if not next_page:
                break
            
            page += 1
            self._wait()
        
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
            
            # 物件名
            title_elem = listing_elem.select_one('.property_unit-title')
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)
            
            # 価格
            price_elem = listing_elem.select_one('.dottable-value')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                data['price'] = self._parse_price(price_text)
            
            # 詳細情報（面積、間取り、築年数など）
            detail_items = listing_elem.select('.dottable-line')
            for detail in detail_items:
                label_elem = detail.select_one('.dottable-title')
                value_elem = detail.select_one('.dottable-value')
                
                if not label_elem or not value_elem:
                    continue
                
                label = label_elem.get_text(strip=True)
                value = value_elem.get_text(strip=True)
                
                # 面積
                if '専有面積' in label:
                    data['area'] = self._parse_area(value)
                
                # 間取り
                elif '間取り' in label:
                    data['layout'] = value
                
                # 階数
                elif '階' in label and '階建' not in label:
                    floor_match = re.search(r'(\d+)階', value)
                    if floor_match:
                        data['floor'] = int(floor_match.group(1))
                
                # 築年数
                elif '築年数' in label or '築年月' in label:
                    year_match = re.search(r'(\d+)年', value)
                    if year_match:
                        data['age_years'] = int(year_match.group(1))
                
                # 方角
                elif '向き' in label or '方角' in label:
                    data['direction'] = value
                
                # 管理費
                elif '管理費' in label:
                    data['management_fee'] = self._parse_price(value)
                
                # 修繕積立金
                elif '修繕積立金' in label:
                    data['repair_reserve'] = self._parse_price(value)
            
            # URL
            link_elem = listing_elem.select_one('a')
            if link_elem and 'href' in link_elem.attrs:
                data['url'] = urljoin(self.BASE_URL, link_elem['href'])
                
                # 詳細ページから追加情報を取得
                detail_data = self._fetch_detail_info(data['url'])
                if detail_data:
                    data.update(detail_data)
            
            # 掲載日（可能な場合）
            date_elem = listing_elem.select_one('.property_unit-date')
            if date_elem:
                data['posted_date'] = date_elem.get_text(strip=True)
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse listing: {e}")
            return None
    
    def _fetch_detail_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        詳細ページから追加情報を取得する
        
        Args:
            url: 物件詳細ページのURL
        
        Returns:
            Dict: 詳細情報（面積、階数、築年数、方角、管理費、修繕積立金、掲載日）
        """
        try:
            self.logger.info(f"Fetching detail page: {url}")
            soup = self._get_page(url)
            if not soup:
                return None
            
            detail_data = {}
            
            # すべてのth/td ペアを抽出
            tables = soup.select('table')
            for table in tables:
                rows = table.select('tr')
                for row in rows:
                    # 1行に複数のth/tdペアがある場合に対応
                    ths = row.select('th')
                    tds = row.select('td')
                    
                    # th要素とtd要素をペアにする
                    for i, th in enumerate(ths):
                        # 対応するtd要素を取得（同じインデックス）
                        if i < len(tds):
                            td = tds[i]
                        else:
                            continue
                        
                        label = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        
                        # 専有面積
                        if '専有面積' in label:
                            area = self._parse_area(value)
                            if area:
                                detail_data['area'] = area
                        
                        # 所在階
                        elif '所在階' in label and '構造' not in label:
                            floor = self._parse_floor(value)
                            if floor:
                                detail_data['floor'] = floor
                        
                        # 所在階/構造（階数も含まれる場合）
                        elif '所在階/構造' in label or ('所在階' in label and '階建' in label):
                            # 例: "23階/RC48階地下1階建"
                            floor_match = re.search(r'(\d+)階', value)
                            if floor_match:
                                detail_data['floor'] = int(floor_match.group(1))
                        
                        # 築年数（築年月から計算）
                        elif '築年' in label or '完成時期' in label:
                            # 例: "2014年12月" or "築10年"
                            year_match = re.search(r'(\d{4})年', value)
                            if year_match:
                                year = int(year_match.group(1))
                                current_year = 2025  # 現在の年
                                detail_data['age_years'] = current_year - year
                            else:
                                # "築10年" の形式
                                age_match = re.search(r'築(\d+)年', value)
                                if age_match:
                                    detail_data['age_years'] = int(age_match.group(1))
                        
                        # 方角（重要：「向き」フィールド）
                        elif '向き' in label:
                            # 方角の抽出
                            direction_match = re.search(r'([東西南北]+)', value)
                            if direction_match:
                                detail_data['direction'] = direction_match.group(1)
                            # 階数が含まれている場合はスキップ
                            elif not re.search(r'\d+階', value):
                                # 階数以外の値であればそのまま使用
                                if value and value != '-':
                                    detail_data['direction'] = value
                        
                        # バルコニー方角からも抽出を試みる
                        elif 'バルコニー' in label:
                            direction_match = re.search(r'([東西南北]+)', value)
                            if direction_match and 'direction' not in detail_data:
                                detail_data['direction'] = direction_match.group(1)
                        
                        # 管理費
                        elif '管理費' in label:
                            fee = self._parse_price(value)
                            if fee:
                                detail_data['management_fee'] = fee
                        
                        # 修繕積立金
                        elif '修繕積立金' in label:
                            fee = self._parse_price(value)
                            if fee:
                                detail_data['repair_reserve'] = fee
                        
                        # 情報提供日
                        elif '情報提供日' in label:
                            # 例: "2025年12月11日"
                            detail_data['posted_date'] = value
            
            # dlからも情報を取得（情報提供日など）
            dls = soup.select('dl')
            for dl in dls:
                dt = dl.select_one('dt')
                dd = dl.select_one('dd')
                if dt and dd:
                    label = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    
                    if '情報提供日' in label and 'posted_date' not in detail_data:
                        detail_data['posted_date'] = value
            
            self._wait()  # 詳細ページ取得後も待機
            return detail_data
        
        except Exception as e:
            self.logger.error(f"Failed to fetch detail page {url}: {e}")
            return None
