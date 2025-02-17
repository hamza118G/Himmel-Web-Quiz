from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import sqlite3
 
app = Flask(__name__)
CORS(app)
 
# File path to the dataset
file_path = r'../data/Q Bank COMPLETE.xlsx'
BOOKMARKS_DB = r'../bookmarks.db'
DB_PATH = r'../stats.db'
 
 
 
try:
    dataset = pd.read_excel(file_path)
    dataset = dataset[[
        "Question Number", "Question", "Category", "Option A", "Option B", 
        "Option C", "Option D", "Correct Answer", "Explanation", 
        "Question Image", "Explanation Image"
    ]]
    dataset = dataset.dropna(subset=["Question Number", "Question"])
    dataset["Question Number"] = dataset["Question Number"].astype(int)
    dataset["Category"] = dataset["Category"].astype(str).str.strip().str.lower()
    dataset = dataset.drop_duplicates(subset=["Question Number"])
    dataset.set_index("Question Number", inplace=True)
    dataset.sort_index(inplace=True)
    print("Dataset loaded and preprocessed successfully.")
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = pd.DataFrame()
 
# User-specific tracking (in-memory storage for simplicity)
user_data = {
    "total_quizzes": 0,
    "total_questions": 0,
    "total_correct": 0,
    "total_incorrect": 0,
    "category_scores": {},  # {category: {"attempted": x, "correct": y}}
    "exam_history": []  # List of past exams
}
 
# User-specific tracking (populated from the database on startup)
user_data = {}
 
def initialize_database():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
 
        # Create the stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                total_quizzes INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                total_incorrect INTEGER DEFAULT 0
            )
        """)
 
        # Create the category_scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_scores (
                category TEXT PRIMARY KEY,
                attempted INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0
            )
        """)
 
        # Insert initial values if stats table is empty
        cursor.execute("SELECT COUNT(*) FROM stats")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO stats (total_quizzes, total_questions, total_correct, total_incorrect) VALUES (0, 0, 0, 0)")
 
        conn.commit()
    print("Database initialized successfully.")
def fetch_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
 
        # Fetch overall stats
        cursor.execute("SELECT * FROM stats")
        stats = cursor.fetchone()
 
        # Fetch category scores
        cursor.execute("SELECT category, attempted, correct FROM category_scores")
        category_scores = {row[0]: {"attempted": row[1], "correct": row[2]} for row in cursor.fetchall()}
 
    return {
        "total_quizzes": stats[0],
        "total_questions": stats[1],
        "total_correct": stats[2],
        "total_incorrect": stats[3],
        "category_scores": category_scores
    }
 
def update_stats(total_attempted, correct_count, incorrect_count, category_scores):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
 
        # Update overall stats
        cursor.execute("""
            UPDATE stats SET
            total_quizzes = total_quizzes + 1,
            total_questions = total_questions + ?,
            total_correct = total_correct + ?,
            total_incorrect = total_incorrect + ?
        """, (total_attempted, correct_count, incorrect_count))
 
        # Update category scores
        for category, scores in category_scores.items():
            cursor.execute("""
                INSERT INTO category_scores (category, attempted, correct)
                VALUES (?, ?, ?)
                ON CONFLICT(category) DO UPDATE SET
                attempted = attempted + EXCLUDED.attempted,
                correct = correct + EXCLUDED.correct
            """, (category, scores["attempted"], scores["correct"]))
 
        conn.commit()
 
@app.route('/log_results', methods=['POST'])
def log_results():
    try:
        data = request.json
        print("Received data for logging results:", data)  # Debugging
 
        total_attempted = data.get("total_attempted", 0)
        correct_count = data.get("correct_count", 0)
        incorrect_count = data.get("incorrect_count", 0)
        category_scores = data.get("category_scores", {})
 
        update_stats(total_attempted, correct_count, incorrect_count, category_scores)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error logging results: {e}")
        return jsonify({"success": False, "error": "Could not log results."})
 
 
 
 
 
 
# Endpoint to fetch exam analytics
@app.route('/get_exam_analytics', methods=['GET'])
def get_exam_analytics():
    try:
        stats = fetch_stats()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        print(f"Error fetching exam analytics: {e}")
        return jsonify({"success": False, "error": "Could not fetch analytics."})
 
 
# Endpoint to evaluate an exam
@app.route('/evaluate_exam', methods=['POST'])
def evaluate_exam():
    try:
        data = request.json
        print("Received payload:", data)  # Debugging
 
        answers = data.get("answers", [])
        if not answers:
            return jsonify({"success": False, "error": "No answers provided."})
 
        print("Parsed answers:", answers)  # Log parsed answers
 
        results = []
        correct_count = 0
        incorrect_count = 0
        category_scores = {}
 
        for answer in answers:
            question_number = answer.get("question_number")
            user_answer = answer.get("user_answer")
 
            print(f"Processing question {question_number}, user answer: {user_answer}")  # Debugging
 
            if question_number not in dataset.index:
                print(f"Question {question_number} not found in dataset.")  # Log missing questions
                continue
 
            question_data = dataset.loc[question_number]
            correct_answer = question_data["Correct Answer"].strip().upper()
            category = question_data["Category"]
 
            if category not in category_scores:
                category_scores[category] = {"attempted": 0, "correct": 0}
 
            is_correct = user_answer == correct_answer
            if is_correct:
                correct_count += 1
                category_scores[category]["correct"] += 1
 
            incorrect_count += not is_correct
            category_scores[category]["attempted"] += 1
 
            results.append({
                "question": question_data["Question"],
                "options": {
                    "A": question_data["Option A"],
                    "B": question_data["Option B"],
                    "C": question_data["Option C"],
                    "D": question_data["Option D"]
                },
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": question_data["Explanation"],
                "question_image": question_data["Question Image"] if pd.notna(question_data["Question Image"]) else None,
                "explanation_image": question_data["Explanation Image"] if pd.notna(question_data["Explanation Image"]) else None,
                "question_number": question_number,
                "category": category
            })
 
        total_attempted = correct_count + incorrect_count
        print(f"Total attempted: {total_attempted}, Correct: {correct_count}, Incorrect: {incorrect_count}")
        print("Category scores:", category_scores)
 
        return jsonify({
            "success": True,
            "results": {
                "score": round((correct_count / total_attempted) * 100, 2) if total_attempted > 0 else 0,
                "correct_count": correct_count,
                "incorrect_count": incorrect_count,
                "total_attempted": total_attempted,
                "category_scores": category_scores,
                "questions": results
            }
        })
    except Exception as e:
        print(f"Error evaluating exam: {e}")
        return jsonify({"success": False, "error": "An error occurred while evaluating the exam."})
 
 
if __name__ == '__main__':
    initialize_database()
    app.run(debug=True, port=5001)
 