import sqlite3
from flask import Flask, request, jsonify, g, Blueprint
from datetime import datetime

app = Flask(__name__)
DATABASE = 'inscription.db'

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
        DROP TABLE IF EXISTS etudiant;
        CREATE TABLE etudiant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            date_naissance TEXT NOT NULL,
            code_permanent TEXT UNIQUE NOT NULL
        );
        ''')

def generer_code_permanent(nom, prenom, date_naissance):
    date_str = datetime.strptime(date_naissance, "%Y-%m-%d").strftime("%d%m%y")
    return (nom[:3] + prenom[:1] + date_str + "01").upper()

@app.route('/inscription/etudiant', methods=['POST'])
def inscrire_etudiant():
    data = request.get_json()
    nom = data.get('nom')
    prenom = data.get('prenom')
    date_naissance = data.get('date_naissance')
    if not nom or not prenom or not date_naissance:
        return jsonify({"error": "Champs manquants"}), 400
    code_permanent = generer_code_permanent(nom, prenom, date_naissance)
    db = get_db()
    try:
        db.execute(
            'INSERT INTO etudiant (nom, prenom, date_naissance, code_permanent) VALUES (?, ?, ?, ?)',
            (nom, prenom, date_naissance, code_permanent)
        )
        db.commit()
        etudiant_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    except sqlite3.IntegrityError:
        return jsonify({"error": "Code permanent déjà utilisé"}), 400
    return jsonify({
        "id": etudiant_id,
        "nom": nom,
        "prenom": prenom,
        "date_naissance": date_naissance,
        "code_permanent": code_permanent
    }), 201

@app.route('/inscription/etudiant/<int:etudiant_id>', methods=['GET'])
def get_etudiant(etudiant_id):
    db = get_db()
    etudiant = db.execute('SELECT * FROM etudiant WHERE id = ?', (etudiant_id,)).fetchone()
    if etudiant is None:
        return jsonify({"error": "Étudiant non trouvé"}), 404
    return jsonify(dict(etudiant))

@app.route('/inscription/etudiant/<int:etudiant_id>', methods=['PUT'])
def update_etudiant(etudiant_id):
    data = request.get_json()
    nom = data.get('nom')
    prenom = data.get('prenom')
    date_naissance = data.get('date_naissance')

    if not nom or not prenom or not date_naissance:
        return jsonify({"error": "Champs manquants pour mise à jour"}), 400

    code_permanent = generer_code_permanent(nom, prenom, date_naissance)
    db = get_db()

    # Vérifier que l'étudiant existe
    etudiant = db.execute('SELECT * FROM etudiant WHERE id = ?', (etudiant_id,)).fetchone()
    if etudiant is None:
        return jsonify({"error": "Étudiant non trouvé"}), 404

    try:
        db.execute('''
            UPDATE etudiant
            SET nom = ?, prenom = ?, date_naissance = ?, code_permanent = ?
            WHERE id = ?
        ''', (nom, prenom, date_naissance, code_permanent, etudiant_id))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Code permanent déjà utilisé par un autre étudiant"}), 400

    etudiant = db.execute('SELECT * FROM etudiant WHERE id = ?', (etudiant_id,)).fetchone()
    return jsonify(dict(etudiant))

@app.route('/inscription/etudiant/<int:etudiant_id>', methods=['DELETE'])
def delete_etudiant(etudiant_id):
    db = get_db()
    etudiant = db.execute('SELECT * FROM etudiant WHERE id = ?', (etudiant_id,)).fetchone()
    if etudiant is None:
        return jsonify({"error": "Étudiant non trouvé"}), 404

    db.execute('DELETE FROM etudiant WHERE id = ?', (etudiant_id,))
    db.commit()
    return jsonify({"message": f"Étudiant {etudiant_id} supprimé avec succès."})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
