-- Schéma applicatif de Loupe, séparé des tables internes de n8n (schéma public).
CREATE SCHEMA IF NOT EXISTS loupe;

CREATE TABLE IF NOT EXISTS loupe.analyses (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entreprise         text        NOT NULL,
    url                text        NOT NULL,
    -- Non utilisé dans le MVP ; prévu pour l'instance perso (jamais affiché en démo)
    type_opportunite   text        CHECK (type_opportunite IN ('cdi', 'mission', 'autre')),
    statut             text        NOT NULL DEFAULT 'en_cours'
                                   CHECK (statut IN ('en_cours', 'termine', 'erreur')),
    teardown           jsonb,
    proof_of_work      jsonb,
    modele             text,
    duree_ms           integer,
    erreur             text,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS analyses_created_at_idx ON loupe.analyses (created_at DESC);
CREATE INDEX IF NOT EXISTS analyses_entreprise_idx ON loupe.analyses (lower(entreprise));
