import scrapy
import re
import json


class ExpertSpider(scrapy.Spider):
    name = "expertspider"
    allowed_domains = ["expert.cz"]
    
    start_urls = ['https://www.expert.cz/']
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS': 1,
    }
    
    def parse(self, response):
        """Parse homepage to find category links"""
        
        self.logger.info("🏠 Parsing Expert.cz homepage...")
        
        # Find category links
        category_links = response.css('nav a::attr(href), .menu a::attr(href), #menu a::attr(href)').getall()
        
        if not category_links:
            # Broader search
            category_links = response.css('a[href]::attr(href)').getall()
        
        # Deduplicate and filter
        unique_categories = set()
        for link in category_links:
            full_url = response.urljoin(link)
            
            # Keep product category pages
            if any(keyword in full_url.lower() for keyword in [
                '/pocitace', '/notebooky', '/mobilni', '/telefon', '/tablet', 
                '/tv', '/televiz', '/monitor', '/audio', '/foto', '/gaming',
                '/tiskarn', '/spotrebice', '/prac', '/lednick', '/myck'
            ]):
                # Skip non-product pages
                if not any(skip in full_url.lower() for skip in [
                    'kontakt', 'o-nas', 'kosik', 'prihlaseni', 'registrace',
                    'obchodni-podminky', 'reklamace', 'doprava', 'cookies'
                ]):
                    unique_categories.add(full_url)
        
        self.logger.info(f"Found {len(unique_categories)} categories")
        
        # Visit each category
        for category_url in sorted(unique_categories):
            self.logger.info(f"📂 Queuing: {category_url}")
            yield scrapy.Request(category_url, callback=self.parse_category, dont_filter=True)
    
    def parse_category(self, response):
        """Parse category page"""
        
        self.logger.info(f"🔍 Parsing: {response.url}")
        
        # Extract products
        product_count = 0
        for item in self.parse_products(response):
            if item and isinstance(item, dict) and 'title' in item:
                product_count += 1
                yield item
            elif hasattr(item, 'url'):
                yield item
        
        if product_count > 0:
            self.logger.info(f"✅ Found {product_count} products")
    
    def parse_products(self, response):
        """Extract products from page"""
        
        category = self.extract_category(response)
        scraped_count = 0
        
        # Method 1: Try JSON data in scripts
        scripts = response.css('script::text').getall()
        
        for script in scripts:
            # Look for JSON-LD Product data
            if '"@type":"Product"' in script or '"@type": "Product"' in script:
                try:
                    # Find product JSON objects
                    for match in re.finditer(r'\{[^{]*"@type"\s*:\s*"Product".*?\}', script, re.DOTALL):
                        try:
                            data = json.loads(match.group(0))
                            if 'name' in data:
                                price_str = None
                                if 'offers' in data:
                                    offers = data['offers']
                                    if isinstance(offers, dict):
                                        price_str = offers.get('price')
                                    elif isinstance(offers, list) and offers:
                                        price_str = offers[0].get('price')
                                
                                yield {
                                    'title': data.get('name'),
                                    'price': self.parse_price(str(price_str)) if price_str else None,
                                    'link': response.urljoin(data.get('url', '')),
                                    'category': category,
                                    'rating': None,
                                }
                                scraped_count += 1
                        except:
                            pass
                except:
                    pass
            
            # Look for product lists in JavaScript
            if '"products"' in script or '"items"' in script:
                try:
                    # Try to extract product arrays
                    for pattern in [r'"products"\s*:\s*\[(.*?)\]', r'"items"\s*:\s*\[(.*?)\]']:
                        match = re.search(pattern, script, re.DOTALL)
                        if match:
                            try:
                                products_json = json.loads(f"[{match.group(1)}]")
                                for item in products_json:
                                    if isinstance(item, dict) and 'name' in item:
                                        yield {
                                            'title': item.get('name'),
                                            'price': self.parse_price(str(item.get('price', ''))),
                                            'link': response.urljoin(item.get('url', '')),
                                            'category': category,
                                            'rating': None,
                                        }
                                        scraped_count += 1
                            except:
                                pass
                except:
                    pass
        
        # Method 2: HTML parsing
        if scraped_count == 0:
            scraped_count = yield from self.parse_html(response, category)
        
        if scraped_count == 0:
            self.logger.warning(f"⚠️ No products found on {response.url}")
        
        # Pagination - also save it for debugging
        next_page = (
            response.css('a.next::attr(href)').get() or
            response.css('a[rel="next"]::attr(href)').get() or
            response.css('.pagination a:contains("›")::attr(href)').get() or
            response.css('.paging .next a::attr(href)').get() or
            response.css('a:contains("Další")::attr(href)').get() or
            response.css('a[href*="page="]::attr(href)').getall()[-1:][0] if response.css('a[href*="page="]') else None
        )
        
        if next_page:
            self.logger.info(f"➡️ Following pagination: {next_page}")
            yield response.follow(next_page, callback=self.parse_category, dont_filter=True)
        else:
            self.logger.debug("No more pagination found")
    
    def parse_html(self, response, category):
        """Parse HTML to extract products"""
        
        # Expert.cz uses <div class="product">
        products = response.css('div.product')
        
        if not products:
            self.logger.warning(f"No products found on {response.url}")
            return 0
        
        self.logger.info(f"Found {len(products)} products")
        
        count = 0
        for product in products:
            # Extract title from <a class="product__name">
            title = product.css('a.product__name::text').get()
            
            if not title:
                title = product.css('.product__name::text').get()
            
            if not title:
                continue
            
            title = title.strip()
            
            if len(title) < 3:
                continue
            
            # Extract price from <div class="product__main-price">
            price_text = (
                product.css('.product__main-price::text').get() or
                product.css('.product__price::text').get() or
                product.css('.product__base-price::text').get() or
                product.css('.price::text').get()
            )
            
            # If not found, try to find price in all text
            if not price_text:
                all_text = ' '.join(product.css('*::text').getall())
                price_match = re.search(r'(\d[\d\s,.]*)\s*Kč', all_text)
                if price_match:
                    price_text = price_match.group(1)
            
            price = self.parse_price(price_text)
            
            # Extract link from <a class="product__name">
            link = product.css('a.product__name::attr(href)').get()
            
            if not link:
                link = product.css('.product__name::attr(href)').get()
            
            if link:
                link = response.urljoin(link)
            
            # Extract rating if available
            rating_text = product.css('.rating::text, [class*="rating"]::text').get()
            rating = self.parse_rating(rating_text)
            
            count += 1
            yield {
                'title': title,
                'price': price,
                'link': link,
                'category': category,
                'rating': rating,
            }
        
        return count
    
    def extract_category(self, response):
        """Extract category from breadcrumbs or URL"""
        # Try breadcrumbs
        breadcrumbs = response.css('.breadcrumbs a::text, .breadcrumb a::text').getall()
        if breadcrumbs:
            categories = [b.strip() for b in breadcrumbs if b.strip().lower() not in ['home', 'domů', 'úvod', 'expert']]
            if categories:
                return categories[-1]
        
        # Try h1
        h1 = response.css('h1::text').get()
        if h1:
            return h1.strip()
        
        # Extract from URL
        url_parts = response.url.rstrip('/').split('/')
        for part in reversed(url_parts):
            if part and part not in ['www.expert.cz', 'expert.cz']:
                category = part.replace('-', ' ').title()
                if len(category) > 2:
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