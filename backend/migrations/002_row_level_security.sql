CREATE OR REPLACE FUNCTION app_business_lines() RETURNS text[]
    LANGUAGE sql STABLE
AS $$
    SELECT coalesce(
        string_to_array(nullif(current_setting('app.business_lines', true), ''), ','),
        ARRAY[]::text[]
    )
$$;

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;

CREATE POLICY documents_by_business_line ON documents
    USING (business_line = ANY (app_business_lines()))
    WITH CHECK (business_line = ANY (app_business_lines()));

CREATE POLICY chunks_by_business_line ON chunks
    USING (business_line = ANY (app_business_lines()))
    WITH CHECK (business_line = ANY (app_business_lines()));

GRANT USAGE ON SCHEMA public TO brisamar_app;
GRANT SELECT, INSERT, UPDATE ON documents TO brisamar_app;
GRANT SELECT, INSERT, DELETE ON chunks TO brisamar_app;
GRANT SELECT, INSERT ON embedding_cache TO brisamar_app;
GRANT EXECUTE ON FUNCTION app_business_lines() TO brisamar_app;
