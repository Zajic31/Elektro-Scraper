import sqlite3
from itemadapter import ItemAdapter

# The class name MUST be 'ScraperPipeline' to match the entry in settings.py:
# ITEM_PIPELINES = { "Scraper.pipelines.ScraperPipeline": 300 }
class ScraperPipeline:
    
    def open_spider(self, spider):
        # 1. Connect to the central database file
        self.conn = sqlite3.connect('comparison_data.db')
        self.cur = self.conn.cursor()
        
        # 2. Create the products table if it doesn't exist
        # PRIMARY KEY (title, source_site) ensures one unique row per product per site, 
        # enabling the INSERT OR REPLACE INTO behavior.
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                title TEXT,
                price REAL,
                rating REAL,
                link TEXT,
                source_site TEXT,
                crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (title, source_site)
            )
        """)
        self.conn.commit()
        spider.logger.info("Database connection opened and 'products' table ensured.")


    def close_spider(self, spider):
        # Close the database connection when the spider finishes
        if self.conn:
            self.conn.close()
            
            
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # 3. Use INSERT OR REPLACE INTO for overwriting
        # The row is replaced entirely if the combination of (title, source_site) exists.
        try:
            self.cur.execute("""
                INSERT OR REPLACE INTO products (title, price, rating, link, source_site)
                VALUES (?, ?, ?, ?, ?)
            """, (
                adapter.get('title'),
                adapter.get('price'),
                adapter.get('rating'),
                adapter.get('link'),
                spider.name  # Stores 'dtrspider', 'alza_spider', etc.
            ))
            
            self.conn.commit()
        
        except Exception as e:
            spider.logger.error(f"Error inserting item into database: {e}")
            # You might want to log the item or raise DropItem here if it's a critical failure