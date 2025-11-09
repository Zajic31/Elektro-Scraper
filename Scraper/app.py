import sqlite3
# Musíme importovat i send_from_directory
from flask import Flask, render_template, request, jsonify, send_from_directory 

DATABASE = 'comparison_data.db' 
app = Flask(__name__)

# --- 1. Pomocné Funkce pro Databázi ---

def get_db_connection():
    """Vytvoří a vrátí spojení s databází."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Aby se výsledky vracely jako slovníky
    return conn

def fetch_all_products():
    """Načte VŠECHNY produkty pro hlavní zobrazení a filtry."""
    conn = get_db_connection()
    
    # PŘEDPOKLAD: Tvá tabulka se jmenuje 'products'
    # POZNÁMKA: V tvé DB se prodejce jmenuje 'source_site' (BEZ pomlčky), tak to musí být i v SELECT
    sql_query = """
        SELECT title, price, rating, link, source_site, category 
        FROM products 
    """ 
    # !!! ODSTRANĚNO: LIMIT 100 !!!
    
    results = [dict(row) for row in conn.execute(sql_query).fetchall()]
    conn.close()
    return results

def search_database(query):
    """Provede vyhledávání podle dotazu (používá se pro /search)."""
    conn = get_db_connection()
    
    # !!! OPRAVA: Přidán 'category' do SELECT, aby se modální okno vykreslilo !!!
    sql_query = """
        SELECT title, price, rating, link, source_site, category
        FROM products 
        WHERE title LIKE ?
    """
    
    search_term = f'%{query}%'
    results = [dict(row) for row in conn.execute(sql_query, (search_term,)).fetchall()]
    conn.close()
    
    return results

# --- 2. Flask Routes (URL Endpoints) ---

@app.route('/', methods=['GET'])
def index():
    """Načte hlavní šablonu (index.html)."""
    # Musíme použít render_template, pokud je index.html ve složce 'templates'
    # Pokud je index.html vedle app.py, musíme ho servírovat jako statický soubor
    try:
        return render_template('index.html')
    except:
        # Fallback, pokud není složka 'templates'
        return send_from_directory('.', 'index.html')


# Endpoint pro hlavní načtení dat (používán app.js)
@app.route('/api/products', methods=['GET'])
def api_products():
    """Vrátí všechna data pro hlavní zobrazení a filtry v JSONu."""
    products = fetch_all_products()
    return jsonify(products)


# Endpoint pro vyhledávání (používán app.js)
@app.route('/search', methods=['POST'])
def search_api():
    """Zpracuje AJAX POST dotaz a vrátí JSON výsledky pro modální okno."""
    data = request.get_json()
    search_query = data.get('query', '').strip()
    
    if search_query:
        results = search_database(search_query)
        return jsonify({'results': results})
        
    return jsonify({'results': []}) 


# --- 3. Route pro Statické Soubory ---
# Aby Flask našel app.js, style.css a loga uvnitř podsložky static/
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    app.run(debug=True)