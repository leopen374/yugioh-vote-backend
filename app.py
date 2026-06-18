from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os
import time

app = Flask(__name__)
CORS(app)  # enable CORS for all routes
HEARTBEAT_ACTIVE = False

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
ADMIN_PAGE = '''<!doctype html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Admin - Yu-Gi-Oh Vote</title>
    <style>
        body {font-family: Arial, sans-serif; margin: 20px; background:#0d0d0d; color:#ffd700;}
        .container {max-width: 600px; margin:auto;}
        h1 {text-align:center;}
        label {display:block; margin-top:10px;}
        input, select {width:100%; padding:8px; margin-top:5px;}
        button {margin-top:15px; padding:10px 20px; background:#ffd700; color:#0d0d0d; border:none; cursor:pointer;}
        button:hover {background:#ffeb3b;}
        .section {border:2px solid #ffd700; padding:15px; margin-top:20px; border-radius:8px;}
        pre {background:#1a1a1a; padding:10px; border-radius:4px; overflow:auto;}
        .small {font-size:0.9em; color:#ccc;}
        .status {margin-top:10px; padding:10px; background:#1a1a1a; border-radius:4px;}
        .status.closed {color:#ffeb3b; border:1px solid #ffd700;}
        .status.open {color:#aaa;}
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
            <button type="submit" style="margin-top:15px; padding:10px 20px; background:#ffd700; color:#0d0d0d; border:none; cursor:pointer;">Sauvegarder la configuration</button>
        </form>
    </div>
    <div class="section">
        <h2>Clôturer le vote</h2>
        <label for="winnerSelect">Sélectionner le vainqueur :</label>
        <select id="winnerSelect">
            <option value="1">-- Choix du personnage 1 --</option>
            <option value="2">-- Choix du personnage 2 --</option>
        </select>
        <br>
        <button id="closeVoteBtn">Clôturer le vote et déclarer le vainqueur</button>
        <div id="closeStatus" class="status">Statut : vote ouvert</div>
    </div>
    <div class="section">
        <h2>Actions</h2>
        <button id="resetBtn">Réinitialiser les votes</button>
        <button id="newVoteBtn">Lancer un nouveau vote</button>
        <div class="section">
        <h2>Heartbeat (keep‑alive)</h2>
        <button id="heartbeatBtn">Activer le heartbeat maintenant</button>
        <div id="heartbeatStatus" class="status">Statut : inactif</div>
    </div>
</div>
    <div class="section">
        <h2>État actuel</h2>
        <pre id="state">Chargement...</pre>
    </div>
</div>
<script>
    const API = window.location.origin; // same origin as admin page
    const winnerSelect = document.getElementById('winnerSelect');
    const closeVoteBtn = document.getElementById('closeVoteBtn');
    const closeStatus = document.getElementById('closeStatus');
    const statePre = document.getElementById('state');
    
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
            document.getElementById('char2').value = config.char2 || '';
            document.getElementById('vote_cooldown').value = config.vote_cooldown || '';
            document.getElementById('max_votes_per_user').value = config.max_votes_per_user || '';
            // populate winner select with actual names
            winnerSelect.options[0].text = `${config.char1} (Personnage 1)`;
            winnerSelect.options[1].text = `${config.char2} (Personnage 2)`;
            // update status
            if (config.voting_closed) {
                const winnerName = config.winner === 1 ? config.char1 : config.winner === 2 ? config.char2 : 'Inconnu';
                closeStatus.textContent = `Statut : vote clôturé – Vainqueur : ${winnerName}`;
                closeStatus.className = 'status closed';
                closeVoteBtn.disabled = true;
            } else {
                closeStatus.textContent = `Statut : vote ouvert`;
                closeStatus.className = 'status open';
                closeVoteBtn.disabled = false;
            }
            statePre.textContent = JSON.stringify({config, votes}, null, 2);
        } catch (e) {
            statePre.textContent = 'Erreur de chargement: ' + e;
        }
    }
    
    closeVoteBtn.addEventListener('click', async () => {
        const winner = winnerSelect.value;
        if (!winner) {
            alert('Veuillez sélectionner un vainqueur.');
            return;
        }
        if (!confirm(`Clôturer le vote et déclarer ${winnerSelect.options[winnerSelect.selectedIndex].text.split(' (')[0]} comme vainqueur ?`)) {
            return;
        }
        try {
            const resp = await fetch(`${API}/config`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({voting_closed: true, winner: parseInt(winner, 10)})
            });
            if (!resp.ok) throw new Error('Erreur serveur');
            alert('Vote clôturé avec succès');
            loadState();
        } catch (err) {
            alert('Erreur: ' + err);
        }
    });
    
    document.getElementById('configForm').addEventListener('submit', async e => {
        e.preventDefault();
        const title = document.getElementById('title').value.trim();
        const char1 = document.getElementById('char1').value.trim();
        const char2 = document.getElementById('char2').value.trim();
        const vote_cooldown = document.getElementById('vote_cooldown').value.trim();
        const max_votes_per_user = document.getElementById('max_votes_per_user').value.trim();
        const payload = {title, char1, char2};
        if (vote_cooldown !== '') payload.vote_cooldown = parseInt(vote_cooldown, 10);
        if (max_votes_per_user !== '') payload.max_votes_per_user = parseInt(max_votes_per_user, 10);
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

    document.getElementById('heartbeatBtn').addEventListener('click', async () => {
        const btn = document.getElementById('heartbeatBtn');
        const statusDiv = document.getElementById('heartbeatStatus');
        btn.disabled = true;
        btn.textContent = 'Activation…';
        try {
            const resp = await fetch(`${API}/counts`);
            if (!resp.ok) throw new Error('Erreur serveur');
            statusDiv.textContent = 'Statut : heartbeat activé (ping réussi)';
            statusDiv.className = 'status closed';
            alert('Heartbeat déclenché avec succès');
        } catch (err) {
            statusDiv.textContent = 'Statut : erreur';
            statusDiv.className = 'status open';
            alert('Erreur: ' + err);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Activer le heartbeat maintenant';
        }
    });

    // Heartbeat status polling
    const heartbeatBtn = document.getElementById('heartbeatBtn');
    const heartbeatStatus = document.getElementById('heartbeatStatus');
    async function updateHeartbeatStatus() {
        try {
            const resp = await fetch(`${API}/heartbeat-status`);
            if (!resp.ok) throw new Error('Failed to fetch heartbeat status');
            const data = await resp.json();
            if (data.active) {
                heartbeatStatus.textContent = 'Statut : heartbeat actif (ping réussi)';
                heartbeatStatus.className = 'status closed';
            } else {
                heartbeatStatus.textContent = 'Statut : heartbeat inactif';
                heartbeatStatus.className = 'status open';
            }
        } catch (err) {
            heartbeatStatus.textContent = 'Statut : erreur';
            heartbeatStatus.className = 'status open';
            console.error(err);
        }
    }
    // Initial load
    updateHeartbeatStatus();
    // Refresh every 30 seconds
    setInterval(updateHeartbeatStatus, 30000);
    // Optional: keep existing heartbeatBtn click to trigger a manual ping
    heartbeatBtn.addEventListener('click', async () => {
        const btn = heartbeatBtn;
        btn.disabled = true;
        btn.textContent = 'Ping…';
        try {
            const resp = await fetch(`${API}/counts`);
            if (!resp.ok) throw new Error('Erreur serveur');
            alert('Heartbeat déclenché avec succès');
        } catch (err) {
            alert('Erreur: ' + err);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Activer le heartbeat maintenant';
        }
    });

</script>
</body>
</html>'''

@app.route('/admin', methods=['GET'])
def admin():
    return render_template_string(ADMIN_PAGE)

@app.route(\'/heartbeat-status\')
def heartbeat_status():
    return jsonify({\"active\": HEARTBEAT_ACTIVE})

if __name__ == '__main__':
    # Start heartbeat thread to keep backend alive
    import threading, time, urllib.request
    def heartbeat():
        HEARTBEAT_ACTIVE = True
        while True:
            try:
                urllib.request.urlopen('http://localhost:5000/counts', timeout=5)
            except Exception:
                pass
            time.sleep(900)  # 15 minutes
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False)
