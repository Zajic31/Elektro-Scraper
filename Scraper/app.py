import sqlite3
from flask import Flask, render_template, request

# Initialize Flask application
app = Flask(__name__)

# --- Database Interaction Function ---
def search_database(query):
    """Searches the SQLite database for products matching the query."""
    
    # 1. Connect to the database file
    # Ensure this path matches the file created by your Scrapy pipeline
    conn = sqlite3.connect('comparison_data.db')
    cur = conn.cursor()
    
    # 2. Define the search SQL query
    # It searches for the query string in the 'title' column (case-insensitive)
    sql_query = """
        SELECT title, price, rating, link, source_site 
        FROM products 
        WHERE title LIKE ?
    """
    
    # 3. Execute the query
    # The '%' symbols allow for partial matching
    search_term = f'%{query}%'
    cur.execute(sql_query, (search_term,))
    
    # 4. Fetch all results
    results = cur.fetchall()
    
    # 5. Close the connection
    conn.close()
    
    return results

# --- Flask Routes (URLs) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handles the home page, search form submission, and displays results."""
    
    results = []
    search_query = ""

    if request.method == 'POST':
        # Get the search term from the submitted form
        search_query = request.form.get('search_item', '').strip()
        if search_query:
            # Run the search function
            results = search_database(search_query)

    # Render the HTML template, passing the results and query
    return render_template(
        'index.html', 
        results=results, 
        query=search_query
    )

if __name__ == '__main__':
    # Run the application
    # You can access it in your browser at http://127.0.0.1:5000/
    app.run(debug=True)