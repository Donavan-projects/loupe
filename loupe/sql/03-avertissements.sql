-- v2.2 : termes réglementaires cités par l'analyse mais absents des pages lues
-- (liste d'objets { terme, champ } ; NULL si la vérification n'a pas eu lieu). Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS avertissements jsonb;
