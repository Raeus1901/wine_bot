from flask import Flask, request, jsonify, send_from_directory
import os
from wine_recommender import WineRecommender
import logging

app = Flask(__name__)
sessions = {}
CSV_PATH = "enriched_wine_data_safari.csv"

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if CSV exists
if not os.path.exists(CSV_PATH):
    logger.error(f"CSV file '{CSV_PATH}' not found.")
    raise FileNotFoundError(f"{CSV_PATH} not found.")

@app.route("/")
def serve_index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/conversation", methods=["POST"])
def conversation():
    user_id = request.args.get("user_id")
    if not user_id:
        logger.error("Missing 'user_id' in request.")
        return jsonify({"error": "Missing user_id"}), 400

    if user_id not in sessions:
        try:
            sessions[user_id] = WineRecommender(CSV_PATH)
            logger.debug(f"Initialized WineRecommender for user_id '{user_id}'.")
        except Exception as e:
            logger.error(f"Failed to initialize recommender: {e}")
            return jsonify({"error": f"Failed to initialize recommender: {e}"}), 500

    recommender = sessions[user_id]
    data = request.get_json() or {}
    msg = data.get("message", "").strip()

    if not msg:
        logger.error("Empty message received.")
        return jsonify({"error": "Empty message"}), 400

    if msg.lower() == "reset":
        recommender.reset()
        logger.debug(f"Session for user_id '{user_id}' has been reset.")
        return jsonify({"message": "Session reset. Let’s start fresh!", "options": []})

    try:
        result = recommender.handle_message(msg)
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return jsonify({"error": "An error occurred while processing your request."}), 500

    return jsonify(result)

@app.route("/reset", methods=["POST"])
def reset():
    user_id = request.args.get("user_id")
    if not user_id:
        logger.error("Missing 'user_id' in reset request.")
        return jsonify({"error": "Missing user_id"}), 400

    if user_id in sessions:
        sessions[user_id].reset()
        logger.debug(f"Session for user_id '{user_id}' has been reset via /reset endpoint.")
        return jsonify({"message": "Session reset."})
    else:
        logger.debug(f"No active session found for user_id '{user_id}'.")
        return jsonify({"message": "No active session to reset."}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5001)

