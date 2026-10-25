-- v2.3 : nombre de pages réellement lues par l'agent pendant l'analyse
-- (NULL si le décompte n'a pas eu lieu). Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS nb_pages integer;
