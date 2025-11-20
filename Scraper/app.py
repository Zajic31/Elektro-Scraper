"""
Price Comparison Web Application
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database path
DB_PATH = 'comparison_data.db'

def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def get_categories():
    """Get all unique categories"""
    conn = get_db_connection()
    categories = conn.execute("""
        SELECT DISTINCT category 
        FROM products 
        WHERE category IS NOT NULL AND category != 'Unknown'
        ORDER BY category
    """).fetchall()
    conn.close()
    return [cat['category'] for cat in categories]

def get_products(category=None, search=None, sort_by='price_asc'):
    """Get products with optional filtering and sorting"""
    conn = get_db_connection()
    
    query = """
        SELECT title, price, rating, link, source_site, category
        FROM products
        WHERE 1=1
    """
    params = []
    
    # Filter by category
    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)
    
    # Search filter
    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")
    
    # Sorting
    if sort_by == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY price DESC"
    elif sort_by == 'name_asc':
        query += " ORDER BY title ASC"
    elif sort_by == 'name_desc':
        query += " ORDER BY title DESC"
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return [dict(row) for row in products]

def get_product_comparison(product_name):
    """Get all sellers for a specific product (similar names)"""
    conn = get_db_connection()
    
    # Find products with similar names (fuzzy matching)
    products = conn.execute("""
        SELECT title, price, rating, link, source_site, category
        FROM products
        WHERE title LIKE ?
        ORDER BY price ASC
    """, (f"%{product_name}%",)).fetchall()
    
    conn.close()
    return [dict(row) for row in products]

def get_stats():
    """Get database statistics"""
    conn = get_db_connection()
    
    stats = {
        'total_products': conn.execute("SELECT COUNT(*) as count FROM products").fetchone()['count'],
        'total_datart': conn.execute("SELECT COUNT(*) as count FROM products WHERE source_site = 'dtrspider'").fetchone()['count'],
        'total_mironet': conn.execute("SELECT COUNT(*) as count FROM products WHERE source_site = 'mironetspider'").fetchone()['count'],
        'categories': len(get_categories())
    }
    
    conn.close()
    return stats

@app.route('/')
def index():
    """Homepage - show all products"""
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'price_asc')
    
    categories = get_categories()
    products = get_products(category, search, sort_by)
    stats = get_stats()
    
    return render_template('index.html', 
                         products=products, 
                         categories=categories,
                         selected_category=category,
                         search_query=search,
                         sort_by=sort_by,
                         stats=stats)

@app.route('/product/<path:product_name>')
def product_detail(product_name):
    """Product detail page - compare prices across stores"""
    sellers = get_product_comparison(product_name)
    
    return render_template('product_detail.html', 
                         product_name=product_name,
                         sellers=sellers)

@app.route('/api/search')
def api_search():
    """API endpoint for search autocomplete"""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    results = conn.execute("""
        SELECT DISTINCT title 
        FROM products 
        WHERE title LIKE ? 
        LIMIT 10
    """, (f"%{query}%",)).fetchall()
    conn.close()
    
    return jsonify([row['title'] for row in results])

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Database not found: {DB_PATH}")
        print("Run your scrapers first to populate the database!")
    else:
        stats = get_stats()
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║          PRICE COMPARISON WEB APP                            ║
╚══════════════════════════════════════════════════════════════╝

📊 Database Statistics:
   • Total Products: {stats['total_products']}
   • Datart Products: {stats['total_datart']}
   • Mironet Products: {stats['total_mironet']}
   • Categories: {stats['categories']}

🌐 Starting server...
   Open: http://localhost:5000

Press Ctrl+C to stop
        """)
    
    app.run(debug=True, host='0.0.0.0', port=5000)