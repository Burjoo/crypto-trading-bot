-- Initial PostgreSQL setup script
-- Runs once when the container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for full-text search

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE cryptobot TO cryptobot;
