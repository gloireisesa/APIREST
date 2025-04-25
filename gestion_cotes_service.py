import sqlite3
from flask import Flask, request, jsonify, g, Blueprint
import requests

app = Flask(__name__)
DATABASE = 'gestion_cotes.db'
INSCRIPTION_SERVICE_URL = "http://localhost:8080/api/inscription/etudiant"


api = Blueprint('api', __name__, url_prefix='/api')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
        DROP TABLE IF EXISTS cote;
        CREATE TABLE cote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etudiant_id INTEGER NOT NULL,
            matiere TEXT NOT NULL,
            note REAL NOT NULL
        );
        ''')

def etudiant_existe(etudiant_id):
    try:
        r = requests.get(f"{INSCRIPTION_SERVICE_URL}/{etudiant_id}")
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

@app.route('/gestion_cotes/etudiant/<int:etudiant_id>/cotes', methods=['POST'])
def ajouter_cote(etudiant_id):
    if not etudiant_existe(etudiant_id):
        return jsonify({"error": "Étudiant non inscrit"}), 404
    data = request.get_json()
    matiere = data.get('matiere')
    note = data.get('note')
    if not matiere or note is None:
        return jsonify({"error": "Champs 'matiere' et 'note' requis"}), 400
    db = get_db()
    db.execute(
        'INSERT INTO cote (etudiant_id, matiere, note) VALUES (?, ?, ?)',
        (etudiant_id, matiere, note)
    )
    db.commit()
    cote_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    return jsonify({
        "id": cote_id,
        "etudiant_id": etudiant_id,
        "matiere": matiere,
        "note": note
    }), 201

@app.route('/gestion_cotes/etudiant/<int:etudiant_id>/cotes', methods=['GET'])
def get_cotes(etudiant_id):
    if not etudiant_existe(etudiant_id):
        return jsonify({"error": "Étudiant non inscrit"}), 404
    db = get_db()
    cotes = db.execute('SELECT * FROM cote WHERE etudiant_id = ?', (etudiant_id,)).fetchall()
    return jsonify([dict(c) for c in cotes])

@app.route('/gestion_cotes/cote/<int:cote_id>', methods=['PUT'])
def update_cote(cote_id):
    data = request.get_json()
    matiere = data.get('matiere')
    note = data.get('note')

    db = get_db()
    cote = db.execute('SELECT * FROM cote WHERE id = ?', (cote_id,)).fetchone()
    if cote is None:
        return jsonify({"error": "Cote non trouvée"}), 404

    # Mise à jour des champs si fournis, sinon on garde les valeurs existantes
    matiere = matiere if matiere is not None else cote['matiere']
    note = note if note is not None else cote['note']

    db.execute('UPDATE cote SET matiere = ?, note = ? WHERE id = ?', (matiere, note, cote_id))
    db.commit()

    cote_updated = db.execute('SELECT * FROM cote WHERE id = ?', (cote_id,)).fetchone()
    return jsonify(dict(cote_updated))

@app.route('/gestion_cotes/cote/<int:cote_id>', methods=['DELETE'])
def delete_cote(cote_id):
    db = get_db()
    cote = db.execute('SELECT * FROM cote WHERE id = ?', (cote_id,)).fetchone()
    if cote is None:
        return jsonify({"error": "Cote non trouvée"}), 404

    db.execute('DELETE FROM cote WHERE id = ?', (cote_id,))
    db.commit()
    return jsonify({"message": f"Cote {cote_id} supprimée avec succès."})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8089, debug=True)
