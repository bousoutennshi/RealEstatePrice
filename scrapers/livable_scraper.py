"""東急リバブルスクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup

class LivableScraper(BaseScraper):
    """東急リバブルから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://www.livable.co.jp"
    TARGET_URL = "https://www.livable.co.jp/mansion/library/000000810513/"
    
    def get_source_name(self) -> str:
        return "Livable"
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        listings = []
        target_layout = self.property_config['layout'] # e.g. "2LDK"
        
        soup = self._get_page(self.TARGET_URL)
        if not soup:
            self.logger.error("Failed to fetch Livable page")
            return listings
            
        items = soup.select('.m-room-list__item')
        self.logger.info(f"Found {len(items)} items on Livable page")
        
        count = 0
        for item in items:
            listing = self._parse_listing(item)
            if listing:
                # 間取りフィルタリング
                layout = listing.get('layout', '')
                if target_layout in layout:
                    listings.append(listing)
                    count += 1
                else:
                    self.logger.debug(f"Skipping layout: {layout} (Target: {target_layout})")
        
        # 詳細情報の取得
        for i, listing in enumerate(listings):
            if 'url' in listing:
                self.logger.info(f"Fetching details for {listing['title']} ({i+1}/{len(listings)})...")
                details = self._fetch_details(listing['url'])
                if details:
                    listing.update(details)
                self._wait()
                
        self.logger.info(f"Extracted {count} valid listings matching {target_layout}")
        return listings

    def _fetch_details(self, url: str) -> Dict[str, Any]:
        """詳細ページから追加情報を取得"""
        details = {}
        try:
            soup = self._get_page(url)
            if not soup:
                return details
            
            # 詳細情報の抽出（dt要素を起点に探す）
            dts = soup.find_all('dt')
            for dt in dts:
                header = dt.get_text(strip=True)
                
                # 次の要素（dtやdd）に当たるまで兄弟を検索して値を探す
                curr = dt.next_sibling
                while curr:
                    # タグの場合
                    if hasattr(curr, 'name') and curr.name:
                        if curr.name in ['dt', 'tr', 'th']: # 次の項目（ヘッダー）が始まったら終了
                            break
                        value = curr.get_text(strip=True)
                    # テキストノードの場合
                    elif isinstance(curr, str):
                        value = curr.strip()
                    else:
                        value = ""
                        
                    if value:
                        break # 値が見つかったら終了
                    
                    curr = curr.next_sibling # 次へ
                
                if not value:
                    continue
                
                if '管理費' in header and '修繕' not in header:
                    details['management_fee'] = self._parse_price(value)
                elif '修繕積立' in header or '積立金' in header:
                    details['repair_reserve'] = self._parse_price(value)
                elif '築年月' in header or '築年数' in header:
                    # "2021年10月"
                    match = re.search(r'(\d{4})年', value)
                    if match:
                        year = int(match.group(1))
                        details['age_years'] = 2025 - year
                elif ('向き' in header or 'バルコニー' in header) and 'direction' not in details:
                    # 「バルコニー面積」などは除外
                    if '面積' in header:
                        continue
                    details['direction'] = value

            # テーブル行（tr > th, td）のパターンも念のためチェック
            if not details:
                rows = soup.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        header = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        
                        if '管理費' in header and '修繕' not in header:
                             if '平均' in header: continue # 平均額は除外
                             details['management_fee'] = self._parse_price(value)
                        elif '修繕積立' in header:
                            if '平均' in header: continue
                            details['repair_reserve'] = self._parse_price(value)
                        elif '築年月' in header:
                            match = re.search(r'(\d{4})年', value)
                            if match:
                                year = int(match.group(1))
                                details['age_years'] = 2025 - year
                        elif '向き' in header:
                            if '面積' in header: continue
                            details['direction'] = value

        except Exception as e:
            self.logger.warning(f"Failed to fetch details from {url}: {e}")
            
        return details
    
    def _parse_listing(self, item: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        物件要素から情報を抽出する
        
        Args:
            item: BeautifulSoupの要素 (.m-room-list__item)
        
        Returns:
            Dict: 物件データ
        """
        try:
            data = {
                'source': self.get_source_name(),
                'title': self.property_config['name']  # マンション名は固定
            }
            
            # 価格
            price_el = item.select_one('.m-room-list__num')
            if price_el:
                data['price'] = self._parse_price(price_el.get_text(strip=True))
            else:
                return None # 価格がないものはスキップ
            
            # リンク
            link = item.find('a')
            if link and link.get('href'):
                data['url'] = urljoin(self.BASE_URL, link.get('href'))
                
            # 詳細情報（テキストベースで柔軟に解析）
            # HTML構造が不規則(dtに値が入っていたりする)なため、テキスト全体から抽出
            text = item.get_text(separator=' ', strip=True)
            
            # 間取り
            layout_match = re.search(r'間取り[:：]\s*([0-9SLDK\+]+)', text)
            if layout_match:
                data['layout'] = layout_match.group(1)
            
            # 面積
            area_match = re.search(r'専有面積[:：]\s*([\d\.]+)m', text)
            if area_match:
                data['area'] = self._parse_area(area_match.group(1))
                
            # 階数
            floor_match = re.search(r'所在階[:：]\s*(\d+)階', text)
            if floor_match:
                data['floor'] = self._parse_floor(floor_match.group(1))
            
            # 賃貸物件の除外（URLチェック）
            if 'url' in data and '/chintai/' in data['url']:
                self.logger.debug(f"Skipping rental listing: {data['url']}")
                return None
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse Livable listing: {e}")
            return None
