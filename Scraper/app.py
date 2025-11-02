import sqlite3
from flask import Flask, render_template, request, jsonify # Import jsonify here

# Initialize Flask application
app = Flask(__name__)

# --- Database Interaction Function (Same as before) ---
def search_database(query):
    """Searches the SQLite database for products matching the query."""
    
    conn = sqlite3.connect('comparison_data.db')
    cur = conn.cursor()
    
    sql_query = """
        SELECT title, price, rating, link, source_site 
        FROM products 
        WHERE title LIKE ?
    """
    
    search_term = f'%{query}%'
    cur.execute(sql_query, (search_term,))
    
    # Fetch results and include column names for better JSON structure
    columns = [desc[0] for desc in cur.description]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    conn.close()
    
    return results

# --- Flask Routes (URLs) ---

@app.route('/', methods=['GET'])
def index():
    """Handles the initial home page load (GET request)."""
    # Only render the HTML template; search happens via AJAX now.
    return render_template('index.html')


# --- NEW DYNAMIC SEARCH ROUTE ---
@app.route('/search', methods=['POST'])
def search_api():
    """Handles AJAX POST requests from the front-end and returns JSON data."""
    # Get the search term from the JSON payload
    data = request.get_json()
    search_query = data.get('query', '').strip()
    
    if search_query:
        results = search_database(search_query)
        # Return the data as JSON
        return jsonify({'results': results})
        
    return jsonify({'results': []}) # Return empty list if query is empty

if __name__ == '__main__':
    app.run(debug=True)