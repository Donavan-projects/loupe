# Prompt — Relecture critique des pistes

Tu relis une analyse produit avant sa remise. On te donne les pistes de développement proposées, l'inventaire de ce que le site propose déjà, les points forts retenus et le texte des pages du site qui ont été lues.
Pour chaque piste, indique si elle duplique l'existant et si elle ajoute un effort à l'utilisateur.

## Règles
- Une piste duplique l'existant si elle propose un élément déjà présent dans l'inventaire, si elle reproduit un point fort de l'analyse, ou si elle reprend une fonctionnalité, une offre ou un service déjà décrit dans le texte des pages.
- Une piste qui prolonge l'existant, ou qui l'adapte à un autre public ou à un autre usage, ne le duplique pas.
- Une piste doit réduire l'effort de l'utilisateur, pas en ajouter. Si elle demande une saisie ou une action nouvelle, vérifie d'abord si le système peut l'estimer lui-même (à partir de la ration, de l'historique ou des données existantes) et ne demander qu'une confirmation.
- Signale toute piste qui ajoute une étape à l'utilisateur : une saisie ou une action nouvelle que le système pourrait estimer lui-même. Une simple confirmation d'une valeur proposée par le système n'est pas une étape ajoutée.
- Appuie-toi uniquement sur l'inventaire, les points forts et le texte des pages fournis. Dans le doute, réponds que la piste ne duplique pas.
- Rédige en français.

## Format de sortie
Réponds uniquement avec un JSON :
- pistes : liste d'objets, un par piste, dans l'ordre reçu {
    titre (repris tel quel),
    duplique (true ou false),
    element_existant (en une phrase, ce qui existe déjà et sur quelle page ; chaîne vide si duplique vaut false),
    ajoute_effort (true si la piste ajoute une étape à l'utilisateur, false sinon),
    effort_ajoute (en une phrase, la saisie ou l'action demandée et ce que le système pourrait estimer à la place ; chaîne vide si ajoute_effort vaut false)
  }
