from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # enable CORS for all routes

VOTES_FILE = os.path.join(os.path.dirname(__file__), 'votes.json')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

def load_votes():
    if not os.path.exists(VOTES_FILE):
        votes = {"1": 0, "2": 0}
        save_votes(votes)
        return votes
    with open(VOTES_FILE, 'r') as f:
        return json.load(f)

def save_votes(votes):
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        config = {
            "title": "Quel personnage préférez-vous ?",
            "char1": "Personnage 1",
            "char2": "Personnage 2"
        }
        save_config(config)
        return config
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

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

@app.route('/config', methods=['GET'])
def get_config():
    config = load_config()
    return jsonify(config)

@app.route('/config', methods=['POST'])
def set_config():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    data = request.get_json()
    # Validate expected keys
    title = data.get('title')
    char1 = data.get('char1')
    char2 = data.get('char2')
    if title is None or char1 is None or char2 is None:
        return jsonify({"error": "Missing title, char1, or char2"}), 400
    config = {"title": title, "char1": char1, "char2": char2}
    save_config(config)
    return jsonify(config)

@app.route('/reset', methods=['POST'])
def reset_votes():
    votes = {"1": 0, "2": 0}
    save_votes(votes)
    return jsonify(votes)

# Admin page
ADMIN_PAGE = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Admin - Yu-Gi-Oh Vote</title>
    <style>
        body {font-family: Arial, sans-serif; margin: 20px; background:#0d0d0d; color:#ffd700;}
        .container {max-width: 600px; margin:auto;}
        h1 {text-align:center;}
        label {display:block; margin-top:10px;}
        input {width:100%; padding:8px; margin-top:5px;}
        button {margin-top:15px; padding:10px 20px; background:#ffd700; color:#0d0d0d; border:none; cursor:pointer;}
        button:hover {background:#ffeb3b;}
        .section {border:2px solid #ffd700; padding:15px; margin-top:20px; border-radius:8px;}
        pre {background:#1a1a1a; padding:10px; border-radius:4px; overflow:auto;}
    </style>
</head>
<body>
<div class="container">
    <h1>Panel d'administration</h1>
    <div class="section">
        <h2>Configuration du vote</h2>
        <form id="configForm">
            <label for="title">Titre de la page :</label>
            <input type="text" id="title" name="title" required>
            <label for="char1">Nom du personnage 1 :</label>
            <input type="text" id="char1" name="char1" required>
            <label for="char2">Nom du personnage 2 :</label>
            <input type="text" id="char2" name="char2" required>
            <button type="submit">Sauvegarder la configuration</button>
        </form>
    </div>
    <div class="section">
        <h2>Actions</h2>
        <button id="resetBtn">Réinitialiser les votes</button>
        <button id="newVoteBtn">Lancer un nouveau vote</button>
    </div>
    <div class="section">
        <h2>État actuel</h2>
        <pre id="state">Chargement...</pre>
    </div>
</div>
<script>
    const API = window.location.origin; // same origin as admin page
    async function loadState() {
        try {
            const [configResp, votesResp] = await Promise.all([
                fetch(`${API}/config`),
                fetch(`${API}/counts`)
            ]);
            const config = await configResp.json();
            const votes = await votesResp.json();
            document.getElementById('title').value = config.title || '';
            document.getElementById('char1').value = config.char1 || '';
            document.getElementById('char2').value = config.char2 || '';
            document.getElementById('state').textContent = JSON.stringify({config, votes}, null, 2);
        } catch (e) {
            document.getElementById('state').textContent = 'Erreur de chargement: ' + e;
        }
    }
    document.getElementById('configForm').addEventListener('submit', async e => {
        e.preventDefault();
        const title = document.getElementById('title').value.trim();
        const char1 = document.getElementById('char1').value.trim();
        const char2 = document.getElementById('char2').value.trim();
        try {
            const resp = await fetch(`${API}/config`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({title, char1, char2})
            });
            if (!resp.ok) throw new Error('Erreur serveur');
            alert('Configuration sauvegardée');
            loadState();
        } catch (err) {
            alert('Erreur: ' + err);
        }
    });
    document.getElementById('resetBtn').addEventListener('click', async () => {
        if (!confirm('Réinitialiser les votes à zéro ?')) return;
        try {
            const resp = await fetch(`${API}/reset`, {method: 'POST'});
            if (!resp.ok) throw new Error('Erreur serveur');
            alert('Votes réinitialisés');
            loadState();
        } catch (err) {
            alert('Erreur: ' + err);
        }
    });
    document.getElementById('newVoteBtn').addEventListener('click', async () => {
        if (!confirm('Lancer un nouveau vote ? Cela réinitialisera les votes.')) return;
        try {
            const resp = await fetch(`${API}/reset`, {method: 'POST'});
            if (!resp.ok) throw new Error('Erreur serveur');
            alert('Nouveau vote lancé');
            loadState();
        } catch (err) {
            alert('Erreur: ' + err);
        }
    });
    loadState();
</script>
</body>
</html>
"""

@app.route('/admin', methods=['GET'])
def admin():
    return render_template_string(ADMIN_PAGE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
