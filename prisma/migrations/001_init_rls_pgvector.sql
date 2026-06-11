-- Run AFTER `prisma migrate dev` has created the base tables.
-- Adds the pgvector ANN index and Row-Level Security tenant isolation.
--
-- The application must execute, per request, inside a transaction:
--     SET LOCAL app.current_org = '<org-uuid>';
-- so that every tenant-scoped query is automatically filtered.

CREATE EXTENSION IF NOT EXISTS vector;

-- ── Approximate-nearest-neighbour index for RAG (HNSW, cosine distance) ──
CREATE INDEX IF NOT EXISTS idx_chunk_embedding
  ON "KnowledgeChunk"
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Full-text column for hybrid (BM25-style) retrieval fused with ANN.
ALTER TABLE "KnowledgeChunk"
  ADD COLUMN IF NOT EXISTS content_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX IF NOT EXISTS idx_chunk_tsv
  ON "KnowledgeChunk" USING gin (content_tsv);

-- ── Tenant isolation via Row-Level Security ──
ALTER TABLE "KnowledgeChunk" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON "KnowledgeChunk";
CREATE POLICY tenant_isolation ON "KnowledgeChunk"
  USING ("orgId" = current_setting('app.current_org', true)::uuid);

ALTER TABLE "ChatSession" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON "ChatSession";
CREATE POLICY tenant_isolation ON "ChatSession"
  USING ("orgId" = current_setting('app.current_org', true)::uuid);

ALTER TABLE "KnowledgeDocument" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON "KnowledgeDocument";
CREATE POLICY tenant_isolation ON "KnowledgeDocument"
  USING ("orgId" = current_setting('app.current_org', true)::uuid);

ALTER TABLE "Course" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON "Course";
CREATE POLICY tenant_isolation ON "Course"
  USING ("orgId" = current_setting('app.current_org', true)::uuid);

ALTER TABLE "Community" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON "Community";
CREATE POLICY tenant_isolation ON "Community"
  USING ("orgId" = current_setting('app.current_org', true)::uuid);
