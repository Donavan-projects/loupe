# Prompt — Réduction du proof-of-work

Tu reçois la spécification d'un prototype, la durée totale de ses étapes et la durée maximale à respecter.
Réduis son périmètre pour que la somme des heures des étapes ne dépasse pas la durée maximale. Tu ne renvoies que les champs que tu peux modifier : le titre, l'objectif, la valeur pour l'entreprise, la justification et la piste retenue sont conservés tels quels.

## Règles
- Retire des éléments du périmètre et les étapes correspondantes ; ne modifie pas les heures des étapes conservées.
- Rédige les champs comme une spécification autonome, lue pour la première fois. Ne mentionne jamais une version précédente, une réduction, un budget ni une durée cible.
- Le prototype reste démontrable seul, et cohérent avec le titre et l'objectif fournis.
- Rédige en français, de façon concise et concrète ; évite les anglicismes quand un terme français existe (fidélité client, désabonnement, parcours, maquette, rappels). N'invente pas de nom de produit ou de marque pour l'entreprise.
- Écris des phrases complètes et naturelles. N'écris aucune URL ni aucune citation entre crochets.
- Formule les éléments de périmètre positivement : pas de partiel ni de limité.
- Au plus 4 éléments de périmètre, 3 éléments hors périmètre et 5 étapes.
- Longueurs maximales : critère de succès en une phrase de 30 mots ; chaque élément de liste en 20 mots.

## Format de sortie
Réponds uniquement avec un JSON :
- perimetre (liste de 2 à 4 éléments)
- hors_perimetre (liste de 2 à 3 éléments)
- etapes : liste ordonnée de 2 à 5 objets { etape, heures (durée de l'étape, en heures, inchangée pour une étape conservée) }
- critere_de_succes (1 phrase vérifiable)
