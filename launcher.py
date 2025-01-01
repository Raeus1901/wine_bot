#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, send_from_directory, request, jsonify
import os
from wine_recommender import WineRecommender

app = Flask(__name__)

# user_id -> WineRecommender instance
sessions = {}

# CSV file with your wine data (ensure columns match your WineRecommender logic)
CSV_PATH = "enriched_wine_data_safari.csv"

########################
# ROUTES: SERVE STATIC
########################
@app.route("/")
def serve_index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

########################
# API ROUTES
########################
@app.route("/next_question", methods=["GET"])
def next_question():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if user_id not in sessions:
        sessions[user_id] = WineRecommender(CSV_PATH)

    recommender = sessions[user_id]
    question_text = recommender.get_current_question()
    return jsonify({
        "done": recommender.done,
        "message": question_text
    })

@app.route("/answer", methods=["POST"])
def answer():
    """
    This route is REQUIRED so the front-end's POST /answer can succeed.
    Otherwise, you'll get a 404 or a 'connect to server' error.
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    # If user_id not in sessions, create a new recommender
    if user_id not in sessions:
        sessions[user_id] = WineRecommender(CSV_PATH)

    recommender = sessions[user_id]

    data = request.get_json()
    if not data or "answer" not in data:
        return jsonify({"error": "Must provide 'answer' in JSON body"}), 400

    user_answer = data["answer"].strip()
    response_text = recommender.process_answer(user_answer)

    return jsonify({
        "done": recommender.done,
        "message": response_text
    })


@app.route("/reset", methods=["POST"])
def reset():
    """
    Clears the user's session so they can start over.
    """
    user_id = request.args.get("user_id")
    if user_id in sessions:
        del sessions[user_id]
    return jsonify({"message": "Session reset. Call /next_question to begin again."})

########################
# MAIN
########################
if __name__ == "__main__":
    app.run(debug=True, port=5001)


