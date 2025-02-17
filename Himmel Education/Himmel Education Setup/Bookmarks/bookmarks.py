from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# File path to the shared bookmarks database
BOOKMARKS_DB = r'C:\Users\hamza butt\Desktop\imp\11\bookmarks.db'

# Helper function to fetch bookmarks from the database
def fetch_bookmarks_from_db():
    try:
        conn = sqlite3.connect(BOOKMARKS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT question_number, category FROM bookmarks")
        bookmarks = [{"question_number": row[0], "category": row[1]} for row in cursor.fetchall()]
        conn.close()
        return bookmarks
    except Exception as e:
        print(f"Error fetching bookmarks from database: {e}")
        return []


# Endpoint to get all bookmarks
@app.route('/get_bookmarks', methods=['GET'])
def get_bookmarks():
    try:
        bookmarks = fetch_bookmarks_from_db()
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        print(f"Error fetching bookmarks: {e}")
        return jsonify({"success": False, "error": "Could not fetch bookmarks."})

# Endpoint to toggle bookmarks
@app.route('/toggle_bookmark', methods=['POST'])
def toggle_bookmark():
    try:
        data = request.get_json()
        question_number = data.get('question_number')
        category = data.get('category')

        if not question_number or not category:
            return jsonify({"success": False, "error": "Invalid or missing data."})

        result = toggle_bookmark_in_db(question_number, category)
        if result is None:
            return jsonify({"success": False, "error": "Could not toggle bookmark."})
        return jsonify({"success": True, "bookmarked": result})
    except Exception as e:
        print(f"Error in /toggle_bookmark: {e}")
        return jsonify({"success": False, "error": "Internal server error."})

@app.route('/get_bookmark_status', methods=['GET'])
@app.route('/get_bookmark_status', methods=['GET'])
def get_bookmark_status():
    try:
        question_number = request.args.get('question_number', type=int)
        if not question_number:
            return jsonify({"success": False, "error": "Invalid or missing question number."})

        bookmarked = bookmarked(question_number) 
        return jsonify({"success": True, "bookmarked": bookmarked})
    except Exception as e:
        print(f"Error fetching bookmark status: {e}")
        return jsonify({"success": False, "error": "Could not fetch bookmark status."})
def toggle_bookmark_in_db(question_number, category):
    try:
        conn = sqlite3.connect(BOOKMARKS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bookmarks WHERE question_number = ?", (question_number,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("DELETE FROM bookmarks WHERE question_number = ?", (question_number,))
            conn.commit()
            conn.close()
            return False  # Bookmark removed
        else:
            cursor.execute("INSERT INTO bookmarks (question_number, category) VALUES (?, ?)", (question_number, category))
            conn.commit()
            conn.close()
            return True  # Bookmark added
    except Exception as e:
        print(f"Error toggling bookmark: {e}")
        return None



if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5004)
