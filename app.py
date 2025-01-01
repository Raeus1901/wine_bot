#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from flask import Flask, request, jsonify, send_from_directory
from wine_recommender import WineRecommender

app = Flask(__name__)

sessions = {}
CSV_PATH = "enriched_wine_data_safari.csv"

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"{CSV_PATH} not found.")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/conversation", methods=["POST"])
def conversation():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    if user_id not in sessions:
        sessions[user_id] = WineRecommender(CSV_PATH)

    recommender = sessions[user_id]

    data = request.get_json() or {}
    msg = data.get("message","").strip()
    if not msg:
        return jsonify({"error": "Empty message"}), 400

    # If user typed "reset"
    if msg.lower() == "reset":
        recommender.reset()
        return jsonify({"message": "Session reset. Let’s start fresh!", "options": []})

    # Otherwise pass to handle_message
    result = recommender.handle_message(msg)
    # This is a dict with { "message": <string>, "options": <list of strings> }
    return jsonify(result)

@app.route("/reset", methods=["POST"])
def reset():
    user_id = request.args.get("user_id")
    if user_id in sessions:
        sessions[user_id].reset()
    return jsonify({"message": "Session reset."})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
