import scrapy
import json
import re


class MironetSpider(scrapy.Spider):
    name = "mironetspider"
    allowed_domains = ["mironet.cz"]

    # Start from homepage to discover all categories
    start_urls = ['https://www.mironet.cz/']

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS': 1,  # Process one at a time
        'DEPTH_LIMIT': 0,  # No depth limit
    }

    def parse(self, response):
        """Parse homepage to find all category links"""
        
        # Look for category links - they have the +c pattern
        category_links = response.css('a[href*="+c"]::attr(href)').getall()
        
        if not category_links:
            self.logger.warning("No category links found on homepage")
            return
        
        # Deduplicate and filter
        unique_categories = set()
        for link in category_links:
            # Get full URL
            full_url = response.urljoin(link)
            
            # Skip subcategories with long paths (keep only main categories)
            path_parts = full_url.split('/')
            # Count directory levels
            dir_count = len([p for p in path_parts if p and '+c' not in p and 'www.mironet.cz' not in p])
            
            # Keep categories with 1-2 directory levels (main categories)
            if dir_count <= 2 and '+c' in full_url:
                unique_categories.add(full_url)
        
        self.logger.info(f"Found {len(unique_categories)} main categories to scrape")
        
        # Visit each category
        for category_url in sorted(unique_categories):
            self.logger.info(f"📂 Queuing: {category_url}")
            yield scrapy.Request(category_url, callback=self.parse_category, dont_filter=True)
    
    def parse_category(self, response):
        """Parse a category page"""
        
        self.logger.info(f"🔍 Parsing: {response.url}")
        
        # Parse HTML to extract products
        product_count = 0
        for item in self.parse_html(response):
            if item and isinstance(item, dict) and 'title' in item:
                product_count += 1
                yield item
            elif hasattr(item, 'url'):
                # It's a Request (pagination)
                yield item
        
        if product_count > 0:
            self.logger.info(f"✅ Found {product_count} products on this page")
    
    def parse_html(self, response):
        """Parse HTML product listing - extract from JavaScript data"""
        
        # Extract category from URL
        category = self.extract_category(response)
        
        # Find all script tags
        scripts = response.css('script::text').getall()
        
        scraped_count = 0
        found_items = False
        
        for script in scripts:
            # Look for the items array in JavaScript
            if 'items:' in script and 'item_id:' in script:
                self.logger.debug("Found JavaScript with product data!")
                found_items = True
                
                # Extract the items array using regex
                items_match = re.search(r'items:\s*\[(.*?)\](?=\s*[,}])', script, re.DOTALL)
                
                if items_match:
                    items_str = items_match.group(1)
                    
                    # Find all item objects
                    item_pattern = r'\{[^}]*item_id:[^}]*\}'
                    item_matches = re.finditer(item_pattern, items_str, re.DOTALL)
                    
                    for item_match in item_matches:
                        item_str = item_match.group(0)
                        
                        try:
                            # Extract fields using regex
                            item_id = re.search(r'item_id:\s*"([^"]+)"', item_str)
                            item_name = re.search(r'item_name:\s*"([^"]+)"', item_str)
                            price = re.search(r'price:\s*(\d+(?:\.\d+)?)', item_str)
                            
                            if item_name:
                                title = item_name.group(1)
                                
                                # Decode unicode escapes manually
                                unicode_map = {
                                    '\\u00e1': 'á', '\\u00c1': 'Á',
                                    '\\u00e9': 'é', '\\u00c9': 'É',
                                    '\\u00ed': 'í', '\\u00cd': 'Í',
                                    '\\u00f3': 'ó', '\\u00d3': 'Ó',
                                    '\\u00fa': 'ú', '\\u00da': 'Ú',
                                    '\\u00fd': 'ý', '\\u00dd': 'Ý',
                                    '\\u010d': 'č', '\\u010c': 'Č',
                                    '\\u010f': 'ď', '\\u010e': 'Ď',
                                    '\\u011b': 'ě', '\\u011a': 'Ě',
                                    '\\u0148': 'ň', '\\u0147': 'Ň',
                                    '\\u0159': 'ř', '\\u0158': 'Ř',
                                    '\\u0161': 'š', '\\u0160': 'Š',
                                    '\\u0165': 'ť', '\\u0164': 'Ť',
                                    '\\u016f': 'ů', '\\u016e': 'Ů',
                                    '\\u017e': 'ž', '\\u017d': 'Ž',
                                    '\\/': '/',
                                }
                                
                                for code, char in unicode_map.items():
                                    title = title.replace(code, char)
                                
                                price_val = float(price.group(1)) if price else None
                                
                                # Build product URL
                                link = None
                                if item_id:
                                    link = f"https://www.mironet.cz/produkt/d{item_id.group(1)}"
                                
                                scraped_count += 1
                                yield {
                                    'title': title,
                                    'price': price_val,
                                    'link': link,
                                    'category': category,
                                    'rating': None,
                                }
                        except Exception as e:
                            self.logger.debug(f"Error parsing item: {e}")
                            continue
                
                break  # Found the data, no need to check other scripts
        
        if scraped_count == 0 and not found_items:
            self.logger.warning(f"⚠️ No products found in {category}")
        
        # Pagination - look for next page
        next_page = (
            response.css('a.next::attr(href)').get() or
            response.css('a[rel="next"]::attr(href)').get() or
            response.css('.pagination a:contains("›")::attr(href)').get() or
            response.css('.pagination .next a::attr(href)').get()
        )
        
        if next_page:
            self.logger.info(f"➡️ Next page found")
            yield response.follow(next_page, callback=self.parse_category, dont_filter=True)
    
    def extract_category(self, response):
        """Extract category from breadcrumbs or URL"""
        # Try breadcrumbs first
        breadcrumbs = response.css('.breadcrumbs a::text, .breadcrumb a::text').getall()
        if breadcrumbs:
            categories = [b.strip() for b in breadcrumbs if b.strip().lower() not in ['home', 'domů', 'úvod']]
            if categories:
                return categories[-1]
        
        # Extract from URL
        url_parts = response.url.rstrip('/').split('/')
        for part in reversed(url_parts):
            if '+c' in part:
                # Clean up the category name
                category = part.split('+c')[0].replace('-', ' ').title()
                if category:
                    return category
        
        return "Unknown"
    
    def parse_price(self, price_text):
        """Parse price from text"""
        if not price_text:
            return None
        
        price_cleaned = re.sub(r'[^\d,.]', '', str(price_text))
        price_cleaned = price_cleaned.replace(',', '.').replace(' ', '')
        
        try:
            if price_cleaned.count('.') > 1:
                parts = price_cleaned.split('.')
                price_cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
            
            return float(price_cleaned) if price_cleaned else None
        except (ValueError, AttributeError):
            return None