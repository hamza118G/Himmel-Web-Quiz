from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
import os
from flask import send_from_directory
import random

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

file_path = r'../data./Q Bank COMPLETE.xlsx'
BOOKMARKS_DB = r'../bookmarks.db'
IMAGE_BASE_PATH = r'../data/extracted_images'

try:
    dataset = pd.read_excel(file_path)
    dataset = dataset[[
        "Question Number", "Question", "Category", "Option A",
        "Option B", "Option C", "Option D", "Correct Answer",
        "Explanation", "Question Image", "Explanation Image", "Difficulty", "Cat2"  # Add Cat2
    ]]
    dataset = dataset.dropna(subset=["Question Number", "Question"])
    dataset["Question Number"] = dataset["Question Number"].astype(int)
    dataset["Category"] = dataset["Category"].astype(str).str.strip().str.lower()
    dataset["Cat2"] = dataset["Cat2"].astype(str).str.strip().str.lower() if "Cat2" in dataset.columns else None
    dataset = dataset.drop_duplicates(subset=["Question Number"])
    dataset.set_index("Question Number", inplace=True)
    dataset.sort_index(inplace=True)

    dataset["Question Image"] = dataset["Question Image"].apply(
        lambda x: f"http://127.0.0.1:5003/images/{os.path.basename(x)}"
        if pd.notna(x) and os.path.isfile(os.path.join(IMAGE_BASE_PATH, os.path.basename(x)))
        else None
    )
    dataset["Explanation Image"] = dataset["Explanation Image"].apply(
        lambda x: f"http://127.0.0.1:5003/images/{os.path.basename(x)}"
        if pd.notna(x) and os.path.isfile(os.path.join(IMAGE_BASE_PATH, os.path.basename(x)))
        else None
    )
    print("Dataset loaded and preprocessed successfully.")
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = pd.DataFrame()

bookmarks = set()

def get_question_data(question_number):
    try:
        question_number = int(question_number)
        if question_number not in dataset.index:
            return None
        row = dataset.loc[question_number].to_dict()
        row["Question Number"] = question_number
        return row
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

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

def is_question_bookmarked(question_number):
    try:
        conn = sqlite3.connect(BOOKMARKS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bookmarks WHERE question_number = ?", (question_number,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception as e:
        print(f"Error checking bookmark status: {e}")
        return False

def toggle_bookmark_in_db(question_number, category):
    try:
        category = category.strip().lower()
        conn = sqlite3.connect(BOOKMARKS_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bookmarks WHERE question_number = ?", (question_number,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("DELETE FROM bookmarks WHERE question_number = ?", (question_number,))
            conn.commit()
            conn.close()
            return False
        else:
            cursor.execute("INSERT INTO bookmarks (question_number, category) VALUES (?, ?)", (question_number, category))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print(f"Error toggling bookmark: {e}")
        return None

@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        categories = dataset["Category"].drop_duplicates().tolist()
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return jsonify({"success": False, "error": "Could not fetch categories."})

@app.route('/get_cat2', methods=['GET'])
def get_cat2():
    try:
        if "Cat2" not in dataset.columns:
            return jsonify({"success": False, "error": "'Cat2' column not found in dataset."})
        cat2_values = dataset["Cat2"].dropna().drop_duplicates().tolist()
        return jsonify({"success": True, "cat2_values": cat2_values})
    except Exception as e:
        print(f"Error fetching Cat2: {e}")
        return jsonify({"success": False, "error": "Could not fetch Cat2 values."})

@app.route('/get_first_question_by_category', methods=['GET'])
def get_first_question_by_category():
    category = request.args.get('category', type=str)
    if not category:
        return jsonify({"success": False, "error": "Invalid or missing category."})

    try:
        filtered = dataset[dataset["Category"].str.strip().str.lower() == category.strip().lower()]
        if not filtered.empty:
            total_questions = len(filtered)
            random_question_number = random.choice(filtered.index.tolist())
            question_data = get_question_data(random_question_number)
            return jsonify({
                "success": True,
                "data": question_data,
                "total_questions": total_questions
            })
        else:
            return jsonify({"success": False, "error": f"No questions found for category '{category}'."})
    except Exception as e:
        print(f"Error fetching question by category: {e}")
        return jsonify({"success": False, "error": "Could not fetch question by category."})

@app.route('/get_first_question_by_cat2', methods=['GET'])
def get_first_question_by_cat2():
    cat2 = request.args.get('cat2', type=str)
    if not cat2:
        return jsonify({"success": False, "error": "Invalid or missing Cat2."})

    try:
        filtered = dataset[dataset["Cat2"].str.strip().str.lower() == cat2.strip().lower()]
        if not filtered.empty:
            total_questions = len(filtered)
            random_question_number = random.choice(filtered.index.tolist())
            question_data = get_question_data(random_question_number)
            return jsonify({
                "success": True,
                "data": question_data,
                "total_questions": total_questions
            })
        else:
            return jsonify({"success": False, "error": f"No questions found for Cat2 '{cat2}'."})
    except Exception as e:
        print(f"Error fetching question by Cat2: {e}")
        return jsonify({"success": False, "error": "Could not fetch question by Cat2."})

@app.route('/get_question', methods=['GET'])
def get_question():
    category = request.args.get('category', type=str)
    question_number = request.args.get('question_number', type=str)

    try:
        if question_number and question_number.isdigit():
            question_data = get_question_data(question_number)
            if question_data:
                effective_category = category if category else question_data["Category"]
                filtered_questions = dataset[dataset["Category"].str.strip().str.lower() == effective_category.strip().lower()]
                total_questions = len(filtered_questions) if not filtered_questions.empty else 0
                return jsonify({
                    "success": True,
                    "data": question_data,
                    "total_questions": total_questions
                })
            return jsonify({"success": False, "error": f"Question number {question_number} not found."})

        if category:
            filtered_questions = dataset[dataset["Category"].str.strip().str.lower() == category.strip().lower()]
            if not filtered_questions.empty:
                random_question_number = random.choice(filtered_questions.index.tolist())
                question_data = get_question_data(random_question_number)
                total_questions = len(filtered_questions)
                return jsonify({
                    "success": True,
                    "data": question_data,
                    "total_questions": total_questions
                })
            return jsonify({"success": False, "error": f"No questions found for category '{category}'."})

        return jsonify({"success": False, "error": "Category is required when requesting a random question."})
    except Exception as e:
        print(f"Error fetching question: {e}")
        return jsonify({"success": False, "error": "Could not fetch question."})

@app.route('/navigate_question', methods=['GET'])
def navigate_question():
    category = request.args.get('category', type=str)
    cat2 = request.args.get('cat2', type=str)

    if not (category or cat2):
        return jsonify({"success": False, "error": "Category or Cat2 is required for navigation."})

    try:
        if cat2:
            filtered_questions = dataset[dataset["Cat2"].str.strip().str.lower() == cat2.strip().lower()]
        else:
            filtered_questions = dataset[dataset["Category"].str.strip().str.lower() == category.strip().lower()]

        if not filtered_questions.empty:
            random_question_number = random.choice(filtered_questions.index.tolist())
            random_question = get_question_data(random_question_number)
            total_questions = len(filtered_questions)
            return jsonify({
                "success": True,
                "data": random_question,
                "total_questions": total_questions
            })
        return jsonify({"success": False, "error": f"No questions found for the specified filter."})
    except Exception as e:
        print(f"Error fetching random question: {e}")
        return jsonify({"success": False, "error": "An internal server error occurred."})

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

@app.route('/get_bookmarks', methods=['GET'])
def get_bookmarks():
    try:
        bookmarks = fetch_bookmarks_from_db()
        return jsonify({"success": True, "bookmarks": bookmarks})
    except Exception as e:
        print(f"Error fetching bookmarks: {e}")
        return jsonify({"success": False, "error": "Could not fetch bookmarks."})

@app.route('/get_bookmark_status', methods=['GET'])
def get_bookmark_status():
    question_number = request.args.get('question_number', type=int)
    if not question_number:
        return jsonify({"success": False, "error": "Invalid or missing question number."})

    return jsonify({"success": True, "bookmarked": question_number in bookmarks})

@app.route('/images/<path:filename>')
def serve_image(filename):
    try:
        image_path = os.path.join(IMAGE_BASE_PATH, filename)
        if os.path.isfile(image_path):
            return send_from_directory(IMAGE_BASE_PATH, filename)
        else:
            print(f"Image not found: {image_path}")
            return jsonify({"success": False, "error": "Image not found."}), 404
    except Exception as e:
        print(f"Error serving image: {e}")
        return jsonify({"success": False, "error": "An internal server error occurred."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5003)