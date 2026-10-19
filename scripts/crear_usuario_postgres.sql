-- ====================================================================
-- SCRIPT DE PROVISIÓN DE SEGURIDAD PARA POSTGRESQL (LINUX)
-- Usuario de Servicio: ai_readonly (Estricto Solo Lectura)
-- ====================================================================

-- 1. Crear usuario restringido sin permisos de superusuario
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_readonly') THEN
      CREATE ROLE ai_readonly WITH LOGIN PASSWORD 'CAMBIAR_POR_PASSWORD_COMPLEJO';
   END IF;
END
$do$;

-- 2. Revocar cualquier privilegio público residual
REVOKE ALL ON DATABASE sisclin FROM ai_readonly;
REVOKE CREATE ON SCHEMA sisclin FROM ai_readonly;
REVOKE CREATE ON SCHEMA sislab FROM ai_readonly;

-- 3. Conceder solo conexión a la base de datos
GRANT CONNECT ON DATABASE sisclin TO ai_readonly;

-- 4. Conceder USAGE exclusivo en esquemas analíticos
GRANT USAGE ON SCHEMA sisclin TO ai_readonly;
GRANT USAGE ON SCHEMA sislab TO ai_readonly;

-- 5. Conceder SELECT exclusivo en tablas existentes
GRANT SELECT ON ALL TABLES IN SCHEMA sisclin TO ai_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA sislab TO ai_readonly;

-- 6. Garantizar que futuras tablas creadas solo tengan SELECT
ALTER DEFAULT PRIVILEGES IN SCHEMA sisclin GRANT SELECT ON TABLES TO ai_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA sislab GRANT SELECT ON TABLES TO ai_readonly;

-- 7. Forzar 'default_transaction_read_only = on' y timeout a nivel de rol
ALTER ROLE ai_readonly SET default_transaction_read_only = on;
ALTER ROLE ai_readonly SET statement_timeout = '30000'; -- 30 segundos máx
