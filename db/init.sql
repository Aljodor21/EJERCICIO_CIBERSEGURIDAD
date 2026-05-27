-- ══════════════════════════════════════════════════════════════════════════
-- LAB-INSECURE — Datos de prueba con vulnerabilidades intencionales
-- VULNERABILIDADES:
--   [V4] Contraseñas almacenadas en texto plano (sin hash)
--   [V4] Contraseñas débiles y predecibles
-- ══════════════════════════════════════════════════════════════════════════

-- Tabla de usuarios
-- MALO: password en texto plano. Correcto: campo password_hash con bcrypt/argon2
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    password   VARCHAR(100) NOT NULL,   -- <- MAL: texto plano
    email      VARCHAR(100) NOT NULL,
    role       VARCHAR(20)  NOT NULL DEFAULT 'user',
    created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Datos de prueba
-- MALO: contraseñas débiles y predecibles
INSERT INTO users (username, password, email, role) VALUES
    ('admin',   'admin123',   'admin@empresa.com',   'admin'),
    ('carlos',  'pass456',    'carlos@empresa.com',  'user'),
    ('maria',   'qwerty',     'maria@empresa.com',   'user'),
    ('juan',    '123456',     'juan@empresa.com',    'user'),
    ('sofia',   'sofia2024',  'sofia@empresa.com',   'user')
ON CONFLICT (username) DO NOTHING;

-- Tabla de productos (para mostrar que la BD tiene más datos sensibles)
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    price       NUMERIC(10,2),
    description TEXT,
    owner_id    INTEGER REFERENCES users(id)
);

INSERT INTO products (name, price, description, owner_id) VALUES
    ('Servidor AWS EC2',   150.00, 'Instancia t3.medium',  1),
    ('Dominio empresa.co',  12.00, 'Registro anual',        1),
    ('Licencia SSL',        80.00, 'Certificado wildcard',  1)
ON CONFLICT DO NOTHING;

-- ══════════════════════════════════════════════════════════════════════════
-- FIX DE REFERENCIA (comentado — para mostrar en clase cómo debería ser)
-- ══════════════════════════════════════════════════════════════════════════
-- CREATE TABLE users_secure (
--     id            SERIAL PRIMARY KEY,
--     username      VARCHAR(50) NOT NULL UNIQUE,
--     password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash, nunca texto plano
--     email         VARCHAR(100) NOT NULL,
--     role          VARCHAR(20) NOT NULL DEFAULT 'user',
--     last_login    TIMESTAMP,
--     failed_attempts INTEGER DEFAULT 0,    -- para lockout de fuerza bruta
--     created_at    TIMESTAMP NOT NULL DEFAULT NOW()
-- );
