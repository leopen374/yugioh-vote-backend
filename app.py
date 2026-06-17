from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # enable CORS for all routes
DATA_FILE = os.path.join(os.path.dirname(__file__), 'votes.json')

def load_votes():
    if not os.path.exists(DATA_FILE):
        votes = {"1": 0, "2": 0}
        save_votes(votes)
        return votes
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_votes(votes):
    with open(DATA_FILE, 'w') as f:
        json.dump(votes, f)

@app.route('/')
def index():
    return "Yu-Gi-Oh Vote Backend is running. Use /counts (GET) or /vote (POST)."

@app.route('/counts', methods=['GET'])
def get_counts():
    votes = load_votes()
    return jsonify(votes)

@app.route('/vote', methods=['POST'])
def vote():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    data = request.get_json()
    vid = data.get('id')
    if vid in (1, "1"):
        vid_str = "1"
    elif vid in (2, "2"):
        vid_str = "2"
    else:
        return jsonify({"error": "Invalid id, must be 1 or 2"}), 400
    votes = load_votes()
    votes[vid_str] = votes.get(vid_str, 0) + 1
    save_votes(votes)
    return jsonify(votes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)