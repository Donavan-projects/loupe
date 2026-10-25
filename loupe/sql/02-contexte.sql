-- v2.1 : contexte optionnel saisi dans le formulaire
-- (pays, secteurs visés, priorités ou texte de référence). Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS contexte text;
