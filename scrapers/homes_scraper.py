"""HOME'S（ライフルホームズ）スクレイパー"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from scrapers.base_scraper import BaseScraper


class HomesScraper(BaseScraper):
    """HOME'Sから物件データを取得するスクレイパー"""
    
    BASE_URL = "https://www.homes.co.jp"
    
    def get_source_name(self) -> str:
        return "HOMES"
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        スクレイピングを実行する
        
        Returns:
            List[Dict]: 物件データのリスト
        """
        self.logger.info(f"Starting {self.get_source_name()} scraping...")
        
        property_name = self.property_config['name']
        
        listings = []
        
        # 検索パラメータ
        # madori_mcf_for_used_sale_residence=25 (2LDK)
        search_url = "https://www.homes.co.jp/mansion/chuko/list/"
        params = {
            'freeword': property_name,
            'madori_mcf_for_used_sale_residence': '25',
            'cond_count': 0 # ページング用（初期値） 
        }
        
        page = 1
        while True:
            self.logger.info(f"Fetching page {page}...")
            if page > 1:
                params['page'] = page
                
            soup = self._get_page(search_url, params=params)
            if not soup:
                break
            
            self.logger.info(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
            
            # 物件リストの親要素を取得（prg-bukkenNameAnchorを含むコンテナ）
            anchors = soup.select('.prg-bukkenNameAnchor')
            if not anchors:
                self.logger.info("No listings found")
                break
                
            self.logger.info(f"Found {len(anchors)} items on page {page} (approx)")
            
            count = 0
            processed_urls = set()
            
            for anchor in anchors:
                # moduleInner (または module-bukken) まで遡る
                container = anchor.find_parent(class_='module-bukken')
                if not container:
                    continue
                
                # 重複処理（1ページ内に同じ物件が複数表示されることがあるため）
                link = anchor.get('href')
                if link in processed_urls:
                    continue
                processed_urls.add(link)
                
                listing = self._parse_listing(container, anchor)
                if listing:
                    # 物件名チェック（念のため）
                    if property_name in listing.get('title', ''):
                        listings.append(listing)
                        count += 1
            
            self.logger.info(f"Extracted {count} valid listings from page {page}")
            
            # 次のページ判定
            # HOME'Sのページネーション構造を確認
            next_page = soup.select_one('.inner .nextPage') # 一般的なクラス
            if not next_page:
                pagination = soup.select('.paging li')
                if pagination:
                     last_item = pagination[-1]
                     if 'next' not in last_item.get('class', []):
                         # classにnextが含まれていない、かつ現在ページが最後なら終了
                         # 単純に「次へ」ボタンがあるか探す
                         next_link = soup.find('a', string=re.compile('次へ'))
                         if not next_link:
                             break
                else:
                    break

            page += 1
            self._wait()
            
            # 安全のため5ページで打ち切り（無限ループ防止）
            if page > 5:
                break
        
        return listings
    
    def _parse_listing(self, container, anchor) -> Optional[Dict[str, Any]]:
        """
        物件コンテナから情報を抽出する
        
        Args:
            container: 物件全体のコンテナ要素 (.module-bukken)
            anchor: タイトルリンク要素
        
        Returns:
            Dict: 物件データ
        """
        try:
            data = {
                'source': self.get_source_name(),
            }
            
            # タイトル
            data['title'] = anchor.get_text(strip=True)
            
            # URL
            href = anchor.get('href')
            if href:
                data['url'] = urljoin(self.BASE_URL, href)
            
            # moduleBody内の情報を解析
            body = container.select_one('.moduleBody')
            if body:
                # 価格
                price_elem = body.select_one('.price span') or body.select_one('.num-price')
                if price_elem:
                    data['price'] = self._parse_price(price_elem.get_text(strip=True))
                
                # テーブル情報の解析
                # HOME'Sは table.verticalTable にスペックが入っている
                table = body.select_one('table.verticalTable')
                if table:
                    rows = table.select('tr')
                    for row in rows:
                        th = row.select_one('th')
                        td = row.select_one('td')
                        if not th or not td:
                            continue
                        
                        header = th.get_text(strip=True)
                        value = td.get_text(strip=True)
                        
                        if '専有面積' in header:
                            # "85.57m² / 2LDK" のような形式
                            parts = value.split('/')
                            if len(parts) > 0:
                                data['area'] = self._parse_area(parts[0])
                            if len(parts) > 1:
                                data['layout'] = parts[1].strip()
                                
                        elif '構造' in header or '階数' in header:
                            # "RC15階建 / 10階" のような形式
                            if '/' in value:
                                floor_part = value.split('/')[1]
                                data['floor'] = self._parse_floor(floor_part)
                            else:
                                data['floor'] = self._parse_floor(value)
                                
                        elif '築年月' in header:
                            # "2015年2月" -> 築年数計算
                            year_match = re.search(r'(\d{4})年', value)
                            if year_match:
                                year = int(year_match.group(1))
                                current_year = 2025
                                data['age_years'] = current_year - year
                        
                        elif '価格' in header and 'price' not in data:
                             # テーブル内に価格がある場合のバックアップ
                             data['price'] = self._parse_price(value)

                        elif '管理費' in header:
                             data['management_fee'] = self._parse_price(value)

                        elif '修繕積立金' in header:
                             data['repair_reserve'] = self._parse_price(value)

                
            # 管理費・修繕積立金が一覧にない場合、詳細ページ取得が必要だが
            # まずは一覧から取れるだけ取る
            
            return data
        
        except Exception as e:
            self.logger.error(f"Failed to parse listing: {e}")
            return None
