from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
from openpyxl import load_workbook
from io import BytesIO
import base64
import os
from flask import send_from_directory

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BOOKMARKS_DB = r'../bookmarks.db'

# Load and preprocess the dataset
file_path = r'../data./Q Bank COMPLETE.xlsx'
try:
    dataset = pd.read_excel(file_path, sheet_name='Sheet1')
    dataset.columns = dataset.columns.str.strip()  # Clean column names

    required_columns = [
        "Question Number", "Question", "Category", "Option A",
        "Option B", "Option C", "Option D", "Correct Answer",
        "Explanation", "Question Image", "Explanation Image","Difficulty" ,"Cat2"
    ]
    existing_columns = [col for col in required_columns if col in dataset.columns]

    if not {"Question Number", "Question", "Category"}.issubset(existing_columns):
        raise ValueError("Critical columns missing: 'Question Number', 'Question', or 'Category'.")

    dataset = dataset[existing_columns]
    dataset = dataset.dropna(subset=["Question Number", "Question"])
    dataset["Question Number"] = dataset["Question Number"].astype(int)
    dataset["Category"] = dataset["Category"].astype(str).str.strip()

    dataset["Question Image"] = dataset["Question Image"].apply(
        lambda x: f"http://127.0.0.1:5006/images/{os.path.basename(x)}" if pd.notna(x) and os.path.isfile(x) else None
    )
    dataset["Explanation Image"] = dataset["Explanation Image"].apply(
        lambda x: f"http://127.0.0.1:5006/images/{os.path.basename(x)}" if pd.notna(x) and os.path.isfile(x) else None
    )

    dataset.set_index("Question Number", inplace=True)
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = None

# In-memory store for bookmarks
bookmarks = set()

IMAGE_BASE_PATH = r"../data/extracted_images"

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
                # Get first question instead of random
                first_question_number = filtered_questions.index.min()
                question_data = get_question_data(first_question_number)
                total_questions = len(filtered_questions)
                return jsonify({
                    "success": True,
                    "data": question_data,
                    "total_questions": total_questions
                })
            return jsonify({"success": False, "error": f"No questions found for category '{category}'."})

        return jsonify({"success": False, "error": "Category is required when requesting a question."})
    except Exception as e:
        print(f"Error fetching question: {e}")
        return jsonify({"success": False, "error": "Could not fetch question."})





@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        categories = dataset["Category"].drop_duplicates().tolist()
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return jsonify({"success": False, "error": "Could not fetch categories."})





@app.route('/get_first_question_by_category', methods=['GET'])
def get_first_question_by_category():
    category = request.args.get('category', type=str)
    if not category:
        return jsonify({"success": False, "error": "Invalid or missing category."})

    try:
        filtered = dataset[dataset["Category"].str.strip().str.lower() == category.strip().lower()]
        if not filtered.empty:
            total_questions = len(filtered)
            first_question_number = filtered.index.min()
            question_data = get_question_data(first_question_number)
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
        return jsonify({"success": False, "error": "Invalid or missing category."})

    try:
        filtered = dataset[dataset["Cat2"].str.strip().str.lower() == cat2.strip().lower()]
        if not filtered.empty:
            total_questions = len(filtered)
            first_question_number = filtered.index.min()
            question_data = get_question_data(first_question_number)
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


        
@app.route('/navigate_question', methods=['GET'])
def navigate_question():
    category = request.args.get('category', type=str)
    cat2 = request.args.get('cat2', type=str)  # Add cat2 parameter
    current_question = request.args.get('current_question', type=int)
    direction = request.args.get('direction', default='next', type=str)

    if not (category or cat2):
        return jsonify({"success": False, "error": "Category or Cat2 is required for navigation."})

    try:
        # Determine which filter to apply
        if cat2:
            filtered_questions = dataset[dataset["Cat2"].str.strip().str.lower() == cat2.strip().lower()]
        else:
            filtered_questions = dataset[dataset["Category"].str.strip().str.lower() == category.strip().lower()]

        if not filtered_questions.empty:
            total_questions = len(filtered_questions)
            question_numbers = sorted(filtered_questions.index)
            
            if not current_question:
                # If no current question specified, start with first
                question_number = question_numbers[0]
            else:
                current_idx = question_numbers.index(current_question) if current_question in question_numbers else -1
                if current_idx == -1:
                    question_number = question_numbers[0]
                else:
                    if direction == 'next' and current_idx < len(question_numbers) - 1:
                        question_number = question_numbers[current_idx + 1]
                    elif direction == 'back' and current_idx > 0:
                        question_number = question_numbers[current_idx - 1]
                    else:
                        question_number = current_question  # Stay on current if at boundary

            question_data = get_question_data(question_number)
            return jsonify({
                "success": True,
                "data": question_data,
                "total_questions": total_questions
            })
        return jsonify({"success": False, "error": f"No questions found for the specified filter."})
    except Exception as e:
        print(f"Error navigating question: {e}")
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
            return False
        else:
            cursor.execute("INSERT INTO bookmarks (question_number, category) VALUES (?, ?)", (question_number, category))
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        print(f"Error toggling bookmark: {e}")
        return None

@app.route('/get_bookmark_status', methods=['GET'])
def get_bookmark_status():
    question_number = request.args.get('question_number', type=int)
    if not question_number:
        return jsonify({"success": False, "error": "Invalid or missing question number."})

    return jsonify({"success": True, "bookmarked": question_number in bookmarks})

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

def extract_image_as_base64(sheet, cell_address):
    try:
        print(f"Extracting image for cell {cell_address}")
        for image in sheet._images:
            cell = sheet[cell_address]
            if image.anchor._from.row == cell.row - 1 and image.anchor._from.col == cell.column - 1:
                img_byte_arr = BytesIO()
                image.image.save(img_byte_arr, format="PNG")
                img_byte_arr.seek(0)
                return f"data:image/png;base64,{base64.b64encode(img_byte_arr.read()).decode('utf-8')}"
    except Exception as e:
        print(f"Error extracting image from {cell_address}: {e}")
    return None

@app.route('/images/<path:filename>')
def serve_image(filename):
    try:
        image_path = os.path.join(IMAGE_BASE_PATH, filename)
        if os.path.isfile(image_path):
            return send_from_directory(IMAGE_BASE_PATH, filename)
        else:
            return jsonify({"success": False, "error": "Image not found."}), 404
    except Exception as e:
        print(f"Error serving image: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500

@app.route('/get_all_questions', methods=['GET'])
def get_all_questions():
    try:
        if dataset is not None:
            return jsonify({"success": True, "questions": dataset.reset_index().to_dict(orient="records")})
        else:
            return jsonify({"success": False, "error": "Dataset not loaded."})
    except Exception as e:
        print(f"Error fetching all questions: {e}")
        return jsonify({"success": False, "error": "An error occurred while fetching questions."})

@app.route('/debug_dataset', methods=['GET'])
def debug_dataset():
    try:
        if dataset is not None:
            return jsonify({"success": True, "data": dataset.reset_index().to_dict(orient="records")})
        else:
            return jsonify({"success": False, "error": "Dataset not loaded."})
    except Exception as e:
        return jsonify({"success": False, "error": f"Error: {e}"})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5006)