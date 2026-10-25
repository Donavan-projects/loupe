-- Expérience modèles : modèle de rédaction utilisé, tokens consommés et coût estimé en dollars
-- (tokens et coût sont renseignés après l'analyse par loupe/tests/lancer.py). Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS modele_redaction text;
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS tokens_entree integer;
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS tokens_sortie integer;
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS cout_estime numeric(10, 4);
