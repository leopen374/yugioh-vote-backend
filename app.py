from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os
import time

app = Flask(__name__)
CORS(app)  # enable CORS for all routes

VOTES_FILE = os.path.join(os.path.dirname(__file__), 'votes.json')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
IP_DATA_FILE = os.path.join(os.path.dirname(__file__), 'ip_data.json')

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
            "char2": "Personnage 2",
            # "image1": "https://via.placeholder.com/150x200?text=Perso+1",
            # "image2": "https://via.placeholder.com/150x200?text=Perso+2",
            "vote_cooldown": 300,  # 5 minutes default
            "max_votes_per_user": 0,  # 0 = unlimited
            "voting_closed": False,
            "winner": None
        }
        save_config(config)
        return config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        # ensure defaults for any missing keys
        defaults = {
            "title": "Quel personnage préférez-vous ?",
            "char1": "Personnage 1",
            "char2": "Personnage 2",
            # "image1": "https://via.placeholder.com/150x200?text=Perso+1",
            # "image2": "https://via.placeholder.com/150x200?text=Perso+2",
            "vote_cooldown": 300,
            "max_votes_per_user": 0,
            "voting_closed": False,
            "winner": None
        }
        for k, v in defaults.items():
            config.setdefault(k, v)
        return config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_ip_data():
    if not os.path.exists(IP_DATA_FILE):
        return {}
    with open(IP_DATA_FILE, 'r') as f:
        return json.load(f)

def save_ip_data(data):
    with open(IP_DATA_FILE, 'w') as f:
        json.dump(data, f)

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

    config = load_config()
    # If voting is closed, reject vote
    if config.get("voting_closed", False):
        winner_name = config.get("char1") if config.get("winner") == 1 else config.get("char2") if config.get("winner") == 2 else "Inconnu"
        return jsonify({
            "error": f"Le vote est clôturé. Le vainqueur est : {winner_name}",
            "voting_closed": True,
            "winner": config.get("winner")
        }), 429

    cooldown = config.get("vote_cooldown", 300)
    max_votes = config.get("max_votes_per_user", 0)

    ip = request.remote_addr or 'unknown'
    now = time.time()

    ip_data = load_ip_data()
    entry = ip_data.get(ip, {"last_vote": 0, "vote_count": 0})

    # cooldown check
    if entry["last_vote"] > 0:
        elapsed = now - entry["last_vote"]
        if elapsed < cooldown:
            remaining = int(cooldown - elapsed)
            return jsonify({
                "error": f"Please wait {remaining} second(s) before voting again.",
                "cooldown": cooldown,
                "remaining": remaining
            }), 429

    # max votes check
    if max_votes > 0 and entry["vote_count"] >= max_votes:
        return jsonify({
            "error": f"You have reached the maximum of {max_votes} votes.",
            "max_votes": max_votes,
            "vote_count": entry["vote_count"]
        }), 429

    # allowed: record vote
    votes = load_votes()
    votes[vid_str] = votes.get(vid_str, 0) + 1
    save_votes(votes)

    # update ip data
    entry["last_vote"] = now
    entry["vote_count"] += 1
    ip_data[ip] = entry
    save_ip_data(ip_data)

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
    # Load existing config to preserve missing fields
    current = load_config()
    # Update only provided fields
    for key in ["title", "char1", "char2", "vote_cooldown", "max_votes_per_user", "voting_closed", "winner"]:
        if key in data:
            current[key] = data[key]
    save_config(current)
    return jsonify(current)

@app.route('/reset', methods=['POST'])
def reset_votes():
    votes = {"1": 0, "2": 0}
    save_votes(votes)
    # also clear IP data? maybe not, but could reset.
    # We'll keep IP data to prevent abuse across resets? Probably reset IP data too.
    save_ip_data({})
    # Also reset voting_closed and winner?
    config = load_config()
    config["voting_closed"] = False
    config["winner"] = None
    save_config(config)
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
        .img-preview {max-width:150px; max-height:200px; margin-top:5px; border:1px solid #555;}
        .small {font-size:0.9em; color:#ccc;}
        .radio-group {display:flex; gap:15px; margin-top:5px;}
        .radio-group label {display:flex; align-items:center; gap:5px;}
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
            <!-- <label for="image1">URL de l'image du personnage 1 :</label>
            <input type="url" id="image1" name="image1" required>
            <div id="preview1"></div> -->
            <label for="char2">Nom du personnage 2 :</label>
            <input type="text" id="char2" name="char2" required>
            <!-- <label for="image2">URL de l'image du personnage 2 :</label>
            <input type="url" id="image2" name="image2" required>
            <div id="preview2"></div> -->
            <label for="vote_cooldown">Temps minimum entre deux votes (secondes) :</label>
            <input type="number" id="vote_cooldown" name="vote_cooldown" min="0" value="300">
            <div class="small">0 = aucun délai</div>
            <label for="max_votes_per_user">Nombre maximum de votes par utilisateur (0 = illimité) :</label>
            <input type="number" id="max_votes_per_user" name="max_votes_per_user" min="0" value="0">
            <div class="small">0 = illimité</div>
            <fieldset style="border:1px solid #ffd700; padding:10px; margin-top:10px;">
                <legend>Clôturer le vote</legend>
                <label>
                    <input type="checkbox" id="closeVote" name="voting_closed">
                    Clôturer le vote
                </label><br>
                <div id="winnerSelect" style="margin-top:10px; display:none;">
                    <label>Vainqueur :</label>
                    <div class="radio-group">
                        <label><input type="radio" name="winner" value="1"> {{char1}}</label>
                        <label><input type="radio" name="winner" value="2"> {{char2}}</label>
                    </div>
                </div>
            </fieldset>
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
            // fill form
            document.getElementById('title').value = config.title || '';
            document.getElementById('char1').value = config.char1 || '';
            // document.getElementById('image1').value = config.image1 || '';
            document.getElementById('char2').value = config.char2 || '';
            // document.getElementById('image2').value = config.image2 || '';
            document.getElementById('vote_cooldown').value = config.vote_cooldown || '';
            document.getElementById('max_votes_per_user').value = config.max_votes_per_user || '';
            document.getElementById('closeVote').checked = !!config.voting_closed;
            const winnerSelect = document.getElementById('winnerSelect');
            if (config.voting_closed) {
                winnerSelect.style.display = 'block';
                // set radio
                const winnerRadios = document.getElementsByName('winner');
                winnerRadios.forEach(r => {
                    if (r.value == config.winner) r.checked = true;
                });
            } else {
                winnerSelect.style.display = 'none';
            }
            document.getElementById('state').textContent = JSON.stringify({config, votes}, null, 2);
        } catch (e) {
            document.getElementById('state').textContent = 'Erreur de chargement: ' + e;
        }
    }
    // live preview
    // document.getElementById('image1').addEventListener('input', e => {
    //     const url = e.target.value.trim();
    //     const preview = document.getElementById('preview1');
    //     preview.innerHTML = url ? `<img src="${url}" class="img-preview" alt="Preview 1">` : '';
    // });
    // document.getElementById('image2').addEventListener('input', e => {
    //     const url = e.target.value.trim();
    //     const preview = document.getElementById('preview2');
    //     preview.innerHTML = url ? `<img src="${url}" class="img-preview" alt="Preview 2">` : '';
    // });
    // Show winner select when checkbox toggled
    document.getElementById('closeVote').addEventListener('change', e => {
        const winnerSelect = document.getElementById('winnerSelect');
        winnerSelect.style.display = e.target.checked ? 'block' : 'none';
        if (!e.target.checked) {
            // uncheck radios
            const radios = document.getElementsByName('winner');
            radios.forEach(r => r.checked = false);
        }
    });
    document.getElementById('configForm').addEventListener('submit', async e => {
        e.preventDefault();
        const title = document.getElementById('title').value.trim();
        const char1 = document.getElementById('char1').value.trim();
        // const image1 = document.getElementById('image1').value.trim();
        const char2 = document.getElementById('char2').value.trim();
        // const image2 = document.getElementById('image2').value.trim();
        const vote_cooldown = document.getElementById('vote_cooldown').value.trim();
        const max_votes_per_user = document.getElementById('max_votes_per_user').value.trim();
        const voting_closed = document.getElementById('closeVote').checked;
        const winnerRadios = document.getElementsByName('winner');
        let winner = null;
        if (voting_closed) {
            winnerRadios.forEach(r => {
                if (r.checked) winner = parseInt(r.value, 10);
            });
            if (winner === null) {
                alert('Veuillez sélectionner un vainqueur lorsque le vote est clôturé.');
                return;
            }
        }
        const payload = {title, char1, char2};
        if (vote_cooldown !== '') payload.vote_cooldown = parseInt(vote_cooldown, 10);
        if (max_votes_per_user !== '') payload.max_votes_per_user = parseInt(max_votes_per_user, 10);
        payload.voting_closed = voting_closed;
        payload.winner = winner;
        try {
            const resp = await fetch(`${API}/config`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
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