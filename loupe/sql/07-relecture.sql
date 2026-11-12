-- Statut de la relecture critique : 'effectuee', ou 'echec' si elle n'a pas pu être faite
-- (sortie du modèle hors format malgré la seconde tentative). NULL pour les analyses antérieures.
-- Script idempotent.
ALTER TABLE loupe.analyses ADD COLUMN IF NOT EXISTS relecture text CHECK (relecture IN ('effectuee', 'echec'));
