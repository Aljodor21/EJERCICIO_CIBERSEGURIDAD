"""
lab-insecure — backend Flask con vulnerabilidades intencionales
USO EXCLUSIVO ACADÉMICO
"""
import os, logging
from datetime import datetime, timedelta
from functools import wraps

import psycopg2
import jwt
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

JWT_SECRET = os.environ.get("JWT_SECRET", "mysecretkey")
DB_HOST    = os.environ.get("DB_HOST", "db")
DB_PORT    = int(os.environ.get("DB_PORT", 5432))
DB_USER    = os.environ.get("DB_USER", "admin")
DB_PASS    = os.environ.get("DB_PASS", "admin123")
DB_NAME    = os.environ.get("DB_NAME", "labdb")
DEBUG_MODE = os.environ.get("DEBUG", "false").lower() == "true"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )

def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token requerido"}), 401
        try:
            request.user = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated


# ── UI ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ── Health ────────────────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({"status": "ok", "app": "lab-insecure"})


# ════════════════════════════════════════════════════════════════════════
# [V1] SQL INJECTION
# ════════════════════════════════════════════════════════════════════════
@app.route('/login', methods=['POST'])
def login():
    data     = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "username y password requeridos"}), 400
    try:
        conn = get_db()
        cur  = conn.cursor()
        # ← VULNERABLE: concatenación directa → SQL Injection
        query = (f"SELECT id, username, email, role "
                 f"FROM users "
                 f"WHERE username='{username}' AND password='{password}'")
        log.info(f"[LOGIN] {query}")
        cur.execute(query)
        user = cur.fetchone()
        cur.close(); conn.close()
        if user:
            uid, uname, email, role = user
            token = jwt.encode(
                {"user_id": uid, "username": uname, "email": email,
                 "role": role, "exp": datetime.utcnow() + timedelta(days=1)},
                JWT_SECRET, algorithm="HS256"
            )
            return jsonify({"status": "ok", "token": token,
                            "user": {"id": uid, "username": uname, "role": role}})
        return jsonify({"status": "error", "message": "Credenciales incorrectas"}), 401
    except Exception as e:
        if DEBUG_MODE:
            import traceback
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
        return jsonify({"error": "Error interno"}), 500


# ════════════════════════════════════════════════════════════════════════
# [V2] SECRETOS EXPUESTOS
# ════════════════════════════════════════════════════════════════════════
@app.route('/debug')
def debug_info():
    # ← VULNERABLE: expone TODAS las variables de entorno
    return jsonify(dict(os.environ))


# ════════════════════════════════════════════════════════════════════════
# [V2b] FORGE TOKEN — endpoint educativo para demostrar impacto del secreto robado
# ════════════════════════════════════════════════════════════════════════
@app.route('/api/forge', methods=['POST'])
def forge_token():
    """
    Recibe el JWT_SECRET (obtenido del /debug) y forja un token de admin.
    Demuestra el impacto de un secreto expuesto.
    """
    data   = request.get_json(force=True, silent=True) or {}
    secret = data.get("secret", "")
    if secret != JWT_SECRET:
        return jsonify({"error": "Secreto incorrecto"}), 400
    token = jwt.encode(
        {"user_id": 1, "username": "admin", "role": "admin",
         "exp": datetime.utcnow() + timedelta(days=30),
         "note": "Token forjado con secreto robado de /debug"},
        secret, algorithm="HS256"
    )
    return jsonify({"token": token,
                    "message": "Token de admin forjado sin conocer la contraseña."})


# ════════════════════════════════════════════════════════════════════════
# [V3] IDOR
# ════════════════════════════════════════════════════════════════════════
@app.route('/user/<int:user_id>')
@require_token
def get_user(user_id):
    # ← VULNERABLE: no valida que el token pertenezca a user_id
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        if not row:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({"id": row[0], "username": row[1], "email": row[2], "role": row[3]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/users')
@require_token
def list_users():
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM users ORDER BY id")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"email":r[2],"role":r[3]} for r in rows])


# ════════════════════════════════════════════════════════════════════════
# VERSIONES CORREGIDAS
# ════════════════════════════════════════════════════════════════════════
@app.route('/secure/login', methods=['POST'])
def secure_login():
    data     = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"error": "username y password requeridos"}), 400
    try:
        conn = get_db(); cur = conn.cursor()
        # ← CORRECTO: prepared statement
        cur.execute("SELECT id, username, email, role, password FROM users WHERE username = %s",
                    (username,))
        user = cur.fetchone(); cur.close(); conn.close()
        if not user or user[4] != password:
            return jsonify({"error": "Credenciales incorrectas"}), 401
        uid, uname, email, role, _ = user
        token = jwt.encode(
            {"user_id": uid, "username": uname, "role": role,
             "exp": datetime.utcnow() + timedelta(hours=1)},
            JWT_SECRET, algorithm="HS256"
        )
        return jsonify({"status": "ok", "token": token})
    except Exception as e:
        log.error(f"secure_login error: {e}")
        return jsonify({"error": "Error interno"}), 500


@app.route('/secure/user/<int:user_id>')
@require_token
def secure_get_user(user_id):
    uid  = request.user.get("user_id")
    role = request.user.get("role", "user")
    # ← CORRECTO: validar autorización
    if uid != user_id and role != "admin":
        return jsonify({"error": "Acceso denegado"}), 403
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id, username, email, role FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        return jsonify({"error": "No encontrado"}), 404
    return jsonify({"id": row[0], "username": row[1], "email": row[2], "role": row[3]})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)
