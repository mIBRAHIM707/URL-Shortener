from flask import Flask, request, redirect, render_template, jsonify
import sqlite3
import base62  # Make sure you have pybase62 installed: pip install pybase62

app = Flask(__name__)

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect('url_shortener.db')
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn

def generate_short_code(id):
    return base62.encode(id)

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten_url():
    original_url = request.form['url']

    if not is_valid_url(original_url):
        return jsonify({'error': 'Invalid URL'}), 400


    conn = get_db_connection()
    cursor = conn.cursor()

    while True: #collision handling loop
        cursor.execute("INSERT INTO urls (original_url) VALUES (?)", (original_url,))
        conn.commit()
        new_id = cursor.lastrowid
        short_code = generate_short_code(new_id)

        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        if cursor.fetchone() is None: # No collision
            cursor.execute("UPDATE urls SET short_code = ? WHERE id=?", (short_code, new_id))
            conn.commit()
            break  # Exit the loop
        else: # Collision
            cursor.execute("DELETE FROM urls WHERE id = ?", (new_id,))  # Clean up
            conn.commit()
    conn.close()

    short_url = request.host_url + short_code
    return jsonify({'short_url': short_url}), 201

@app.route('/<short_code>')
def redirect_to_original(short_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT original_url, clicks FROM urls WHERE short_code = ?", (short_code,))
    url_data = cursor.fetchone()

    if url_data:
        original_url = url_data['original_url']
        clicks = url_data['clicks']

        cursor.execute("UPDATE urls SET clicks = ? WHERE short_code = ?", (clicks + 1, short_code))
        conn.commit()
        conn.close()

        return redirect(original_url, code=301)
    else:
        conn.close()
        return "URL not found", 404

# --- URL Validation (using regex) ---
import re
def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


if __name__ == '__main__':
    app.run(debug=True)