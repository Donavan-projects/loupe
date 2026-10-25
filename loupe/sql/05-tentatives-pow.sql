-- v2.5 : nombre de générations du proof-of-work (1, ou 2 si le total dépassait 8 h
-- et qu'une correction a été demandée). Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS tentatives_pow integer;
