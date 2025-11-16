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
            # E.g., keep /telefony/mobilni-telefony+c10737/ but skip deeper ones
            path_parts = full_url.split('/')
            # Count directory levels (ignore empty strings from leading/trailing /)
            dir_count = len([p for p in path_parts if p and '+c' not in p and 'www.mironet.cz' not in p])
            
            # Only keep categories with 1-2 directory levels (main categories)
            if dir_count <= 2 and '+c' in full_url and full_url not in unique_categories:
                unique_categories.add(full_url)
        
        self.logger.info(f"Found {len(unique_categories)} main categories to scrape")
        
        # Visit each category
        for category_url in sorted(unique_categories):
            self.logger.info(f"Queuing category: {category_url}")
            yield scrapy.Request(category_url, callback=self.parse_category, errback=self.handle_error)
    
    def handle_error(self, failure):
        """Handle request errors - don't stop the spider"""
        self.logger.error(f"Request failed: {failure.request.url}")
        # Continue with other requests
    
    def parse_category(self, response):
        """Parse a category page"""
        
    def parse_category(self, response):
        """Parse a category page"""
        
        self.logger.info(f"Parsing category page: {response.url}")
        
        # Try to extract category ID from URL (e.g., +c10737)
        category_match = re.search(r'\+c(\d+)', response.url)
        if category_match:
            category_id = category_match.group(1)
            # Try the old API endpoint format (but don't block on it)
            api_url = f"https://www.mironet.cz/rest/produkt/list/?categoryId={category_id}&page=1&limit=50"
            self.logger.debug(f"Trying API with category {category_id}")
            yield scrapy.Request(api_url, callback=self.parse_api, errback=lambda _: None, dont_filter=True)
        
        # Parse HTML - this is the main method
        for item in self.parse_html(response):
            yield item
    
    def parse_api(self, response):
        """Parse JSON API response"""
        try:
            data = json.loads(response.text)
            products = data.get("produkty") or data.get("data") or data.get("products") or []
            
            if products:
                self.logger.info(f"API works! Found {len(products)} products")
                
                for p in products:
                    title = p.get("nazev") or p.get("title")
                    price = p.get("cena_s_dph") or p.get("price")
                    url = p.get("url")
                    rating = p.get("hodnoceni") or p.get("rating")
                    category = p.get("kategorie_nazev") or p.get("category")
                    
                    if url and not url.startswith('http'):
                        url = f"https://www.mironet.cz{url}"
                    
                    if isinstance(price, str):
                        price = float(price.replace(',', '.').replace(' ', ''))
                    
                    if isinstance(rating, str):
                        rating = float(rating.replace(',', '.'))
                    
                    if title:
                        yield {
                            "title": title,
                            "price": price,
                            "link": url,
                            "category": category,
                            "rating": rating,
                        }
                
                # Handle pagination
                current_page = int(data.get("page", 1))
                total_pages = int(data.get("totalPages", 1))
                
                if current_page < total_pages:
                    # Build next page URL
                    next_url = response.url
                    if 'page=' in next_url:
                        next_url = re.sub(r'page=\d+', f'page={current_page + 1}', next_url)
                    else:
                        separator = '&' if '?' in next_url else '?'
                        next_url = f"{next_url}{separator}page={current_page + 1}"
                    
                    yield scrapy.Request(next_url, callback=self.parse_api)
            else:
                # No products in API, try HTML
                self.logger.warning("API returned no products, trying HTML")
                
        except json.JSONDecodeError:
            self.logger.warning("Not JSON, trying HTML parsing")
    
    def parse_html(self, response):
        """Parse HTML product listing - extract from JavaScript data"""
        
        # Extract category from URL
        category = self.extract_category(response)
        
        self.logger.info(f"Extracting products from category: {category}")
        
        # Mironet embeds product data in JavaScript!
        # Look for: items: [ { item_id: "xxx", item_name: "xxx", price: xxx } ]
        
        scraped_count = 0
        
        # Find all script tags
        scripts = response.css('script::text').getall()
        
        found_items = False
        
        for script in scripts:
            # Look for the items array in JavaScript
            if 'items:' in script and 'item_id:' in script:
                self.logger.info("Found JavaScript with product data!")
                found_items = True
                
                # Extract the items array using regex
                # Pattern: items: [ ... ]
                items_match = re.search(r'items:\s*\[(.*?)\](?=\s*[,}])', script, re.DOTALL)
                
                if items_match:
                    items_str = items_match.group(1)
                    
                    # Split by individual items (each starts with {)
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
                                
                                # Decode unicode escapes manually (safer than unicode_escape)
                                # Replace common Czech characters
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
                                
                                # Build product URL from item_id
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
            self.logger.warning(f"Could not find JavaScript product data on {response.url}")
            # Try HTML fallback
            for item in self.parse_html_fallback(response, category):
                scraped_count += 1
                yield item
        
        self.logger.info(f"✅ Scraped {scraped_count} products from {category}")
        
        # Pagination
        next_page = (
            response.css('a.next::attr(href)').get() or
            response.css('a[rel="next"]::attr(href)').get() or
            response.css('.pagination a:contains("›")::attr(href)').get() or
            response.css('.pagination a:contains("Další")::attr(href)').get()
        )
        
        if next_page:
            self.logger.info(f"Following pagination: {next_page}")
            yield response.follow(next_page, callback=self.parse_category)
    
    def parse_html_fallback(self, response, category):
        """Fallback HTML parsing if JavaScript extraction fails"""
        
        products = response.css('[data-product-id], .product-item, .product')
        
        if not products:
            return 0
        
        count = 0
        for idx, product in enumerate(products):
            # Use same extraction logic as before
            title = (
                product.css('h3 a::text').get() or
                product.css('h3::text').get() or
                product.css('h2 a::text').get() or
                product.css('[itemprop="name"]::text').get()
            )
            
            if not title:
                continue
            
            title = ' '.join(title.split()).strip()
            
            price_text = product.css('.price::text, [data-price]::attr(data-price)').get()
            price = self.parse_price(price_text)
            
            link = product.css('a::attr(href)').get()
            if link:
                link = response.urljoin(link)
            
            count += 1
            yield {
                'title': title,
                'price': price,
                'link': link,
                'category': category,
                'rating': None,
            }
        
        return count
    
    def extract_category(self, response):
        """Extract category from breadcrumbs or URL"""
        breadcrumbs = response.css('.breadcrumbs a::text, .breadcrumb a::text').getall()
        if breadcrumbs:
            categories = [b.strip() for b in breadcrumbs if b.strip().lower() not in ['home', 'domů', 'úvod']]
            if categories:
                return categories[-1]
        
        # Extract from URL
        url_parts = response.url.rstrip('/').split('/')
        if url_parts:
            category = url_parts[-1].replace('-', ' ').title()
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
    
    def parse_rating(self, rating_text):
        """Parse rating from text"""
        if not rating_text:
            return None
        
        match = re.search(r'(\d+([.,]\d+)?)', str(rating_text))
        if match:
            try:
                return float(match.group(1).replace(',', '.'))
            except ValueError:
                return None
        return None