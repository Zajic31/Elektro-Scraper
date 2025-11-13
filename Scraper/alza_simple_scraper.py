from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import sqlite3
import time
import re
import os
from datetime import datetime

class AlzaScraper:
    def __init__(self):
        print("Initializing Alza Scraper...")
        
        # Check if database exists
        db_path = 'comparison_data.db'
        if os.path.exists(db_path):
            print(f"✅ Found database: {db_path}")
        else:
            print(f"⚠️ Database not found, will create new one: {db_path}")
        
        # Setup Chrome options
        chrome_options = Options()
        
        # Comment this line to SEE the browser (useful for debugging)
        # chrome_options.add_argument('--headless')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        print("Starting Chrome browser...")
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Browser started successfully")
        except Exception as e:
            print(f"❌ Failed to start browser: {e}")
            print("\nMake sure Chrome and ChromeDriver are installed:")
            print("  pip install selenium")
            print("  Or install manually from: https://chromedriver.chromium.org/")
            raise
        
        # Database connection
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self.ensure_table()
    
    def ensure_table(self):
        """Create table if it doesn't exist"""
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                title TEXT,
                price REAL,
                rating REAL,
                link TEXT,
                source_site TEXT,
                category TEXT,
                crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (title, source_site)
            )
        """)
        self.conn.commit()
        print("✅ Database table ready\n")
    
    def scrape_category(self, url, category_name, max_products=50):
        """Scrape a single category page"""
        print(f"\n{'='*60}")
        print(f"Scraping: {category_name}")
        print(f"URL: {url}")
        print(f"{'='*60}")
        
        try:
            print("Loading page...")
            self.driver.get(url)
            print("Waiting for content to load...")
            time.sleep(5)  # Wait for page to fully load
            
            # Scroll down to trigger lazy loading
            print("Scrolling page to load products...")
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight/{3-i});")
                time.sleep(1)
            
            # Get page source
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find product boxes - try multiple selectors
            products = soup.find_all(['div', 'article'], class_=re.compile(r'(box|browsingitem|product-item|tile)', re.I))
            
            if not products:
                print(f"⚠️ No products found with standard selectors. Trying alternatives...")
                products = soup.find_all(attrs={'data-productid': True})
            
            if not products:
                # Try even more generic approach
                products = soup.find_all(['div', 'article'], attrs={'data-impression-name': True})
            
            print(f"Found {len(products)} potential product elements")
            
            if len(products) == 0:
                print("⚠️ WARNING: No products found. The page structure might have changed.")
                print("Opening browser for 10 seconds so you can see what loaded...")
                time.sleep(10)
            
            saved_count = 0
            for idx, product in enumerate(products[:max_products], 1):
                try:
                    # Extract product name - try multiple approaches
                    item_name = None
                    
                    # Try data attribute first
                    if product.get('data-impression-name'):
                        item_name = product.get('data-impression-name')
                    
                    # Try finding by class
                    if not item_name:
                        name_elem = (
                            product.find('a', class_=re.compile(r'name', re.I)) or
                            product.find('h3') or
                            product.find('h2') or
                            product.find('a', class_=re.compile(r'browsing', re.I))
                        )
                        if name_elem:
                            item_name = name_elem.get_text(strip=True)
                    
                    if not item_name or len(item_name) < 3:
                        continue
                    
                    # Extract price
                    item_price = None
                    
                    # Try data attribute
                    if product.get('data-impression-price'):
                        try:
                            item_price = float(product.get('data-impression-price'))
                        except:
                            pass
                    
                    # Try finding by class
                    if not item_price:
                        price_elem = product.find(class_=re.compile(r'price', re.I))
                        if price_elem:
                            price_text = price_elem.get_text()
                            price_cleaned = re.sub(r'[^\d,.]', '', str(price_text))
                            price_cleaned = price_cleaned.replace(',', '.').replace(' ', '')
                            try:
                                if price_cleaned and price_cleaned.count('.') > 1:
                                    parts = price_cleaned.split('.')
                                    price_cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                                if price_cleaned:
                                    item_price = float(price_cleaned)
                            except ValueError:
                                pass
                    
                    # Extract link
                    item_link = None
                    link_elem = product.find('a', href=True)
                    if link_elem:
                        href = link_elem.get('href')
                        if href:
                            item_link = href if href.startswith('http') else f"https://www.alza.cz{href}"
                    
                    # Extract rating
                    item_rating = None
                    rating_elem = product.find(class_=re.compile(r'rating', re.I))
                    if rating_elem:
                        rating_text = rating_elem.get_text()
                        rating_match = re.search(r'(\d+([.,]\d+)?)', rating_text)
                        if rating_match:
                            try:
                                item_rating = float(rating_match.group(1).replace(',', '.'))
                            except:
                                pass
                    
                    # Save to database
                    self.cur.execute("""
                        INSERT OR REPLACE INTO products (title, price, rating, link, source_site, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (item_name, item_price, item_rating, item_link, 'alza_selenium', category_name))
                    
                    saved_count += 1
                    
                    # Display progress
                    price_str = f"{item_price:.0f} Kč" if item_price else "N/A"
                    rating_str = f"⭐{item_rating}" if item_rating else ""
                    print(f"  [{saved_count:3d}] {item_name[:45]:45s} | {price_str:12s} {rating_str}")
                    
                except Exception as e:
                    # Silent skip for minor errors
                    pass
            
            self.conn.commit()
            print(f"\n✅ Saved {saved_count} products from {category_name}")
            
        except Exception as e:
            print(f"❌ Error scraping category {category_name}: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self, categories=None, max_products_per_category=50):
        """Run the scraper on multiple categories"""
        
        if categories is None:
            categories = [
                ("https://www.alza.cz/notebooky/18842853.htm", "Notebooky"),
                ("https://www.alza.cz/mobily-a-tablety/18856711.htm", "Mobily a tablety"),
                ("https://www.alza.cz/gaming/18859906.htm", "Gaming"),
                # Add more categories as needed
            ]
        
        total_start = time.time()
        
        for url, category in categories:
            self.scrape_category(url, category, max_products=max_products_per_category)
            print(f"Waiting 5 seconds before next category...")
            time.sleep(5)  # Polite delay between categories
        
        total_time = time.time() - total_start
        
        # Print summary
        print(f"\n{'='*60}")
        print("SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        
        # Count total products
        self.cur.execute("SELECT COUNT(*) FROM products WHERE source_site = 'alza_selenium'")
        count = self.cur.fetchone()[0]
        print(f"Total Alza products in database: {count}")
        
        # Show breakdown by category
        self.cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM products 
            WHERE source_site = 'alza_selenium' 
            GROUP BY category
        """)
        print("\nBreakdown by category:")
        for cat, cnt in self.cur.fetchall():
            print(f"  {cat}: {cnt} products")
        
        print(f"{'='*60}\n")
    
    def close(self):
        """Clean up resources"""
        print("\nClosing browser and database...")
        self.driver.quit()
        self.conn.close()
        print("✅ Done!")

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                   ALZA.CZ SCRAPER                            ║
║              Using Selenium + BeautifulSoup                  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    scraper = AlzaScraper()
    try:
        # You can customize categories here
        scraper.run(max_products_per_category=30)  # Limit to 30 products per category for testing
    except KeyboardInterrupt:
        print("\n\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()

if __name__ == "__main__":
    main()