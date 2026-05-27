# lab-insecure

**Laboratorio de vulnerabilidades deliberadas para clase magistral de ciberseguridad**

> Uso exclusivo académico. No desplegar en producción.

---

## Qué incluye

Una aplicación web completa con:

- **UI visual** en el browser — los estudiantes interactúan como si fuera una app real
- **API Flask** con 4 vulnerabilidades intencionales
- **PostgreSQL** con datos de prueba

| Ataque | Ruta vulnerable | Ruta corregida |
|--------|----------------|----------------|
| SQL Injection    | `POST /login`      | `POST /secure/login` |
| Secretos expuestos | `GET /debug`     | No existe (se elimina) |
| Forjar JWT       | `POST /api/forge`  | — |
| IDOR             | `GET /user/:id`    | `GET /secure/user/:id` |

---

## Levantar el lab (tu servidor)

```bash
cd lab-insecure
docker compose up -d
docker compose ps

# Verificar
curl http://localhost:5000/health

# La UI visual está en:
# http://localhost:5000
```

---

## Exponer con Cloudflare Tunnel

### Opción A — Agregar al tunnel existente

Editá `/etc/cloudflared/config.yml`:

```yaml
ingress:
  # tus servicios existentes...
  - hostname: lab.servelejo.site
    service: http://localhost:5000
  - service: http_status:404
```

```bash
sudo systemctl restart cloudflared
# Probar desde celular con datos (red diferente):
curl https://lab.servelejo.site/health
```

### Opción B — Tunnel nuevo

```bash
cloudflared tunnel create lab-clase
cloudflared tunnel route dns lab-clase lab.servelejo.site

cat > /etc/cloudflared/lab.yml << EOF
tunnel: TU-TUNNEL-ID
credentials-file: /root/.cloudflared/TU-TUNNEL-ID.json
ingress:
  - hostname: lab.servelejo.site
    service: http://localhost:5000
  - service: http_status:404
EOF

cloudflared service install --config /etc/cloudflared/lab.yml
sudo systemctl start cloudflared-lab
```

---

## Scripts de arranque / apagado

Guardá como `~/arrancar-lab.sh`:

```bash
#!/bin/bash
cd ~/lab-insecure
docker compose up -d
sleep 8

STATUS=$(curl -s http://localhost:5000/health | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null)

[ "$STATUS" = "ok" ] && echo "Backend OK" || { echo "Backend no responde"; docker compose logs backend; exit 1; }

sudo systemctl start cloudflared
sleep 3

REMOTE=$(curl -s https://lab.servelejo.site/health | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null)

[ "$REMOTE" = "ok" ] \
  && echo "Lab listo en: https://lab.servelejo.site" \
  || echo "Tunnel tardando. Verificar en unos segundos."
```

```bash
chmod +x ~/arrancar-lab.sh ~/apagar-lab.sh
```

`~/apagar-lab.sh`:

```bash
#!/bin/bash
sudo systemctl stop cloudflared
cd ~/lab-insecure && docker compose down
echo "Lab apagado."
```

---

## Lo que hacen los estudiantes

Abrís el browser en `https://lab.servelejo.site` y ya.

**No necesitan instalar Docker.** Solo `curl`, Python 3 y `pip install PyJWT requests`
para los ejercicios de terminal complementarios.

---

## Flujo de la clase en la UI

### Tab 01 — SQL Injection

1. El estudiante intenta login con `admin` / `wrong_password` → ve el error 401
2. Observa la query que se construye en tiempo real abajo del formulario
3. Hace clic en **"Inyectar SQL"** → el campo se llena con `admin'--`
4. Ve cómo la query cambia y la condición de password queda comentada
5. El servidor retorna 200 y un token → impacto visual inmediato
6. Copia el token para usarlo en Tab 03

### Tab 02 — Secretos expuestos

1. Hace clic en **"GET /debug"**
2. Ve todas las variables de entorno — `DB_PASS`, `JWT_SECRET`, etc. resaltadas en rojo
3. El secreto se carga automáticamente en el campo de forjado
4. Hace clic en **"Forjar token de admin"** → obtiene un token de admin sin conocer la contraseña
5. Copia el token

### Tab 03 — IDOR

1. Pega el token de carlos (obtenido con login normal en Tab 01)
2. Pone `user_id = 1` (el admin)
3. Hace clic en **"GET /user/:id"** → ve los datos del admin con el token de carlos
4. Hace clic en **"Enumerar todos"** → lista completa de usuarios del sistema

### Tab FIX — Versiones corregidas

1. Intenta la misma inyección en `/secure/login` → recibe 401 correctamente
2. Intenta IDOR con `/secure/user/1` usando token de carlos → recibe 403
3. Hace login real con credenciales válidas → recibe token, accede a sus propios datos

---

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| UI no carga | Backend caído | `docker compose logs backend` |
| 502 en tunnel | Puerto incorrecto | Verificar `docker compose ps` |
| `/debug` sin JWT_SECRET | Variable no pasada | Revisar `docker-compose.yml` |
| SQL Injection no funciona | BD no lista | Esperar 10s y reintentar |
| Tunnel no responde | DNS no propagado | Esperar 2–5 min |

---

## Estructura

```
lab-insecure/
├── docker-compose.yml
├── README.md
├── backend/
│   ├── app.py            ← Flask: rutas vulnerables + rutas seguras
│   ├── Dockerfile
│   ├── requirements.txt
│   └── static/
│       └── index.html    ← UI visual completa (vanilla JS, sin deps)
└── db/
    └── init.sql          ← Datos de prueba
```

---

*Clase magistral — Diplomado en Ciberseguridad*
