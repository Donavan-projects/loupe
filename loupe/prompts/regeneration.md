# Prompt — Régénération de pistes

Tu reçois une analyse produit, parfois un contexte, le texte des pages du site qui ont été lues, et la liste des pistes à remplacer : chacune duplique un élément existant ou ajoute un effort à l'utilisateur, et le motif t'est indiqué.
Propose une piste de remplacement pour chacune.

## Règles
- La nouvelle piste ne reproduit ni un point fort de l'analyse, ni un élément de son `inventaire_existant`, ni une fonctionnalité décrite dans les pages lues, ni une autre piste de l'analyse : elle ajoute quelque chose à l'existant.
- Une piste doit réduire l'effort de l'utilisateur, pas en ajouter. Si elle demande une saisie ou une action nouvelle, vérifie d'abord si le système peut l'estimer lui-même (à partir d'un calcul déjà proposé par le site, de l'historique ou des données existantes) et ne demander qu'une confirmation.
- Elle s'appuie sur un élément propre à l'entreprise, visible dans les pages lues : pas de piste générique applicable à n'importe quelle entreprise (par exemple « mesurer les gains »). Elle ne porte pas sur un angle de `perimetre_non_couvert`.
- Elle s'appuie sur les pages lues. Si un contexte est fourni, il sert uniquement à la choisir ; ne le présente jamais comme une information sur l'entreprise ou sur le marché.
- Formule-la positivement, comme une opportunité. N'emploie jamais les mots : problème, défaut, faiblesse, manque, échec, friction, critique.
- N'écris aucune URL ni aucune citation entre crochets dans les champs de texte. Le champ `source` contient uniquement l'URL exacte d'une page de `pages_analysees`.
- Réglementation : ne nomme aucune norme, organisme, autorité ni obligation légale, et n'emploie pas les mots certification, homologation ou agrément, s'ils ne figurent pas textuellement dans les pages lues.
- Désigne les clients par leur métier précis.
- Rédige en français, de façon concise ; évite les anglicismes quand un terme français existe (fidélité client, désabonnement, parcours, maquette, rappels). N'invente pas de nom de produit ou de marque pour l'entreprise.

## Format de sortie
Réponds uniquement avec un JSON :
- pistes : liste d'objets, un par piste à remplacer, dans l'ordre reçu {
    remplace (titre de la piste remplacée, repris tel quel),
    titre (court, orienté action),
    opportunite (ce que l'entreprise pourrait gagner, formulé positivement),
    existant (les éléments de inventaire_existant sur ce sujet, en nommant la page source, ou « rien de visible »),
    apport (ce que la piste ajoute à l'existant),
    proposition (la piste concrète),
    impact ("fort"|"moyen"|"faible"),
    effort ("fort"|"moyen"|"faible"),
    source (URL exacte de la page de pages_analysees qui inspire la piste)
  }
