"""
=======================================================
LAB CIBERSEGURIDAD - BACKEND DELIBERADAMENTE VULNERABLE
=======================================================
Este código contiene vulnerabilidades INTENCIONALES para
fines educativos. NUNCA usar en producción.

Vulnerabilidades presentes:
  1. SQL Injection en /login
  2. Endpoint de debug expuesto en /debug
  3. IDOR (Insecure Direct Object Reference) en /user/<id>
  4. CORS abierto para todos los origenes
  5. Contraseñas en texto plano
  6. JWT secret debil
  7. Stack trace expuesto en errores
  8. Proceso corriendo como root
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import jwt
import datetime
import time

app = Flask(__name__)

# MAL: CORS abierto a cualquier origen
CORS(app, origins="*")

SECRET_KEY = os.environ.get('SECRET_KEY', 'defaultsecret')


def get_db():
    retries = 5
    while retries > 0:
        try:
            return psycopg2.connect(
                host=os.environ['DB_HOST'],
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASS'],
                database='labdb'
            )
        except Exception:
            retries -= 1
            time.sleep(2)
    raise Exception("No se pudo conectar a la base de datos")


# -------------------------------------------------------
# VULNERABILIDAD 1: SQL Injection
# La query se construye concatenando strings directamente
# -------------------------------------------------------
@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')

    try:
        conn = get_db()
        cur = conn.cursor()

        # MAL: concatenacion directa = SQL Injection
        query = f"SELECT id, username, role FROM users WHERE username='{username}' AND password='{password}'"
        
        # En modo debug muestra la query completa al cliente
        if os.environ.get('DEBUG') == 'true':
            print(f"[DEBUG] Query ejecutada: {query}")

        cur.execute(query)
        user = cur.fetchone()
        conn.close()

        if user:
            token = jwt.encode(
                {
                    'user_id': user[0],
                    'username': user[1],
                    'role': user[2],
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                },
                SECRET_KEY,
                algorithm='HS256'
            )
            return jsonify({
                'status': 'ok',
                'token': token,
                'username': user[1],
                'role': user[2]
            })
        
        return jsonify({'status': 'error', 'message': 'Credenciales incorrectas'}), 401

    except Exception as e:
        # MAL: expone el error interno completo (stack trace)
        return jsonify({'status': 'error', 'detail': str(e)}), 500


# -------------------------------------------------------
# VULNERABILIDAD 2: Endpoint /debug expuesto
# Devuelve TODAS las variables de entorno del proceso
# -------------------------------------------------------
@app.route('/debug')
def debug():
    # MAL: esto no deberia existir en ninguna app real
    return jsonify({
        'env': dict(os.environ),
        'debug_mode': os.environ.get('DEBUG'),
        'version': os.environ.get('APP_VERSION', 'unknown')
    })


# -------------------------------------------------------
# VULNERABILIDAD 3: IDOR
# Cualquier usuario puede acceder a datos de cualquier otro
# No hay validacion de que el token corresponda al user_id
# -------------------------------------------------------
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # MAL: no se verifica que el token pertenezca a este user_id
    try:
        conn = get_db()
        cur = conn.cursor()
        # MAL: concatenacion directa tambien aqui
        cur.execute(f"SELECT id, username, email, role FROM users WHERE id={user_id}")
        user = cur.fetchone()
        conn.close()

        if user:
            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'role': user[3]
            })
        return jsonify({'error': 'Usuario no encontrado'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# -------------------------------------------------------
# Endpoint de salud (este es correcto, para referencia)
# -------------------------------------------------------
@app.route('/health')
def health():
    return jsonify({'status': 'running', 'app': 'lab-insecure'})


# -------------------------------------------------------
# Endpoint para ver todos los usuarios (sin autenticacion)
# -------------------------------------------------------
@app.route('/users')
def list_users():
    # MAL: sin autenticacion, sin paginacion, sin filtrado
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role FROM users")
        users = cur.fetchall()
        conn.close()
        return jsonify([
            {'id': u[0], 'username': u[1], 'email': u[2], 'role': u[3]}
            for u in users
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # MAL: debug=True en produccion expone el debugger de Werkzeug
    # MAL: host='0.0.0.0' expone en todas las interfaces
    app.run(host='0.0.0.0', port=5000, debug=True)
