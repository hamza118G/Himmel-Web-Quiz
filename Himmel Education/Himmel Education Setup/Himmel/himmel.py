from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import sqlite3
 
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins
 
# File paths
file_path = r'../data/Q Bank COMPLETE.xlsx'
 
DB_PATH = r"../stats.db"
 
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
 
try:
    dataset = pd.read_excel(file_path)
    dataset = dataset[[
        "Question Number", "Question", "Category", "Option A", "Option B",
        "Option C", "Option D", "Correct Answer", "Explanation", "Question Image", "Explanation Image"
    ]]
 
    # Preprocessing
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
 
 
def load_user_data():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
 
        # Fetch overall stats
        cursor.execute("SELECT * FROM stats")
        stats = cursor.fetchone()
        user_data["total_quizzes"] = stats[0]
        user_data["total_questions"] = stats[1]
        user_data["total_correct"] = stats[2]
        user_data["total_incorrect"] = stats[3]
 
        # Fetch category scores
        cursor.execute("SELECT category, attempted, correct FROM category_scores")
        user_data["category_scores"] = {row[0]: {"attempted": row[1], "correct": row[2]} for row in cursor.fetchall()}
 
    print("User data loaded successfully:", user_data)
 
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
 
 
@app.route('/get_exam_analytics', methods=['GET'])
def get_exam_analytics():
    try:
        stats = fetch_stats()  # Reload stats from the database

        # Get total questions per category
        category_data = dataset.groupby("Category").size().to_dict()

        # Calculate total questions
        total_questions = sum(category_data.values())

        # Prepare category-wise score data
        category_scores = {
            cat: {
                "attempted": stats["category_scores"].get(cat, {}).get("attempted", 0),
                "correct": stats["category_scores"].get(cat, {}).get("correct", 0),
                "total_questions": count
            }
            for cat, count in category_data.items()
        }

        # Create the response object with updated total_questions and totalNumberOfQuestion
        response = {
            "total_quizzes": stats["total_quizzes"],
            "total_questions": stats["total_questions"],
            "total_correct": stats["total_correct"],
            "total_incorrect": stats["total_incorrect"],
            "totalNumberOfQuestion": total_questions,  # This will include the sum of total questions from all categories
            "category_scores": category_scores
        }
        print("Returning exam analytics:", response)  # Debug log
        return jsonify({"success": True, "data": response})
    except Exception as e:
        print(f"Error fetching exam analytics: {e}")
        return jsonify({"success": False, "error": "Could not fetch analytics."})

 
 
#  @app.route('/get_exam_analytics', methods=['GET'])
# def get_exam_analytics():
#     try:
#         stats = fetch_stats()  # Reload stats from the database

#         # Get total questions per category
#         category_data = dataset.groupby("Category").size().to_dict()

#         # Calculate total questions
#         total_questions = sum(category_data.values())

#         # Prepare category-wise score data
#         category_scores = {
#             cat: {
#                 "attempted": stats["category_scores"].get(cat, {}).get("attempted", 0),
#                 "correct": stats["category_scores"].get(cat, {}).get("correct", 0),
#                 "total_questions": count
#             }
#             for cat, count in category_data.items()
#         }

#         # Create the response object with updated total_questions
#         response = {
#             "total_quizzes": stats["total_quizzes"],
#             "total_questions": total_questions,  # Sum of all questions across categories
#             "total_correct": stats["total_correct"],
#             "total_incorrect": stats["total_incorrect"],
#             "category_scores": category_scores
#         }
#         print("Returning exam analytics:", response)  # Debug log
#         return jsonify({"success": True, "data": response})
#     except Exception as e:
#         print(f"Error fetching exam analytics: {e}")
#         return jsonify({"success": False, "error": "Could not fetch analytics."})

 
# Endpoint to fetch all unique categories
@app.route('/get_categories', methods=['GET'])
def get_categories():
    try:
        category_data = dataset.groupby("Category").size().to_dict()
        categories = [
            {
                "name": category,
                "total_questions": count,
                "attempted": user_data["category_scores"].get(category, {}).get("attempted", 0)
            }
            for category, count in category_data.items()
        ]
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return jsonify({"success": False, "error": "Could not fetch categories."})
 
# Endpoint to log results after an exam
@app.route('/log_results', methods=['POST'])
def log_results():
    try:
        data = request.json
        print("Received data for logging results:", data)  # Debugging
 
        total_attempted = data.get("total_attempted", 0)
        correct_count = data.get("correct_count", 0)
        incorrect_count = data.get("incorrect_count", 0)
        category_scores = data.get("category_scores", {})
 
        # Update the database
        update_stats(total_attempted, correct_count, incorrect_count, category_scores)
 
        # Synchronize user_data with the database
        load_user_data()  # Ensure user_data reflects the latest stats
 
        print("Results logged successfully! Updated user_data:", user_data)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error logging results: {e}")
        return jsonify({"success": False, "error": "Could not log results."})
 
# Endpoint to reset all stats
@app.route('/reset_stats', methods=['POST'])
def reset_stats():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
 
            # Reset overall stats
            cursor.execute("UPDATE stats SET total_quizzes = 0, total_questions = 0, total_correct = 0, total_incorrect = 0")
            print("Stats table reset.")  # Debug log
 
            # Reset category scores
            cursor.execute("DELETE FROM category_scores")
            print("Category scores table reset.")  # Debug log
 
            conn.commit()
 
        print("User stats have been reset successfully in the database.")
        return jsonify({"success": True, "message": "Stats reset successfully."})
    except Exception as e:
        print(f"Error resetting stats: {e}")
        return jsonify({"success": False, "error": "Could not reset stats."})
 
# Endpoint to create a custom exam
@app.route('/create_exam', methods=['POST'])
def create_exam():
    try:
        data = request.json
        num_questions = data.get("num_questions", 0)
        categories = data.get("categories", [])

        # Validate basic inputs
        if not categories or num_questions <= 0 or num_questions > 200:
            return jsonify({"success": False, "error": "Invalid exam parameters. Please select categories and a valid number of questions (1-200)."})

        # Filter dataset to only include selected categories
        available_questions = dataset[dataset["Category"].isin(categories)]
        if available_questions.empty:
            return jsonify({"success": False, "error": "No questions available for the selected categories."})

        # Calculate questions per category (aim for even distribution)
        total_available = len(available_questions)
        num_questions = min(num_questions, total_available)  # Cap at available questions
        questions_per_category = max(1, num_questions // len(categories)) if categories else 0
        quiz_questions = []

        # Adjust to ensure total questions match num_questions
        remaining_questions = num_questions

        for category in categories:
            if remaining_questions <= 0:
                break

            category_questions = available_questions[available_questions["Category"] == category]
            if category_questions.empty:
                continue  # Skip if no questions are available for this category

            # Determine how many questions to pick from this category
            num_to_sample = min(questions_per_category, remaining_questions, len(category_questions))
            selected_questions = category_questions.sample(n=num_to_sample).reset_index()

            for _, row in selected_questions.iterrows():
                quiz_questions.append({
                    "Question Number": row["Question Number"],
                    "Question": row["Question"],
                    "Category": row["Category"],
                    "Option A": row["Option A"],
                    "Option B": row["Option B"],
                    "Option C": row["Option C"],
                    "Option D": row["Option D"],
                    "Correct Answer": row["Correct Answer"],
                    "Explanation": row["Explanation"],
                    "Question Image": row["Question Image"] if pd.notna(row["Question Image"]) else None,
                    "Explanation Image": row["Explanation Image"] if pd.notna(row["Explanation Image"]) else None
                })

            remaining_questions -= num_to_sample

        # If there are still remaining questions and categories left, distribute them
        if remaining_questions > 0:
            remaining_pool = available_questions[~available_questions.index.isin([q["Question Number"] for q in quiz_questions])]
            if not remaining_pool.empty:
                extra_questions = remaining_pool.sample(n=min(remaining_questions, len(remaining_pool))).reset_index()
                for _, row in extra_questions.iterrows():
                    quiz_questions.append({
                        "Question Number": row["Question Number"],
                        "Question": row["Question"],
                        "Category": row["Category"],
                        "Option A": row["Option A"],
                        "Option B": row["Option B"],
                        "Option C": row["Option C"],
                        "Option D": row["Option D"],
                        "Correct Answer": row["Correct Answer"],
                        "Explanation": row["Explanation"],
                        "Question Image": row["Question Image"] if pd.notna(row["Question Image"]) else None,
                        "Explanation Image": row["Explanation Image"] if pd.notna(row["Explanation Image"]) else None
                    })

        # Check if we fulfilled the request
        if not quiz_questions:
            return jsonify({"success": False, "error": "No questions could be selected for the exam."})

        return jsonify({"success": True, "questions": quiz_questions})
    except Exception as e:
        print(f"Error occurred while creating exam: {e}")
        return jsonify({"success": False, "error": "Could not create exam."})
 
def fetch_stats():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
 
        # Fetch overall stats
        cursor.execute("SELECT * FROM stats")
        stats = cursor.fetchone() or (0, 0, 0, 0)
 
        # Fetch category scores
        cursor.execute("SELECT category, attempted, correct FROM category_scores")
        category_scores = {row[0]: {"attempted": row[1], "correct": row[2]} for row in cursor.fetchall()}
 
    # Update user_data
    global user_data
    user_data = {
        "total_quizzes": stats[0],
        "total_questions": stats[1],
        "total_correct": stats[2],
        "total_incorrect": stats[3],
        "category_scores": category_scores
    }
    print("User data synchronized with database:", user_data)
    return user_data
 
 
if __name__ == '__main__':
    initialize_database()
    load_user_data()  # Ensure user_data is initialized
    app.run(debug=True, port=5000)
 
 