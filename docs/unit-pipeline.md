# Production 3D des unités — exécution locale

Le point d'entrée du pipeline est **scripts/unit-pipeline.py**. Il est propre au projet, peut fonctionner dans un terminal local sans GitHub Actions, et lit une fiche JSON par unité dans **data/units/**.

## Sélectionner une unité

Le format d'entrée est décrit par **data/schemas/unit-manifest.schema.json**. Une nouvelle unité ne nécessite que son identifiant, son nom et le chemin de son illustration originale. Le programme dérive les quatre profils, les chemins du corps 3D et des équipements et les requêtes des modèles. Des champs facultatifs permettent de réutiliser les artéfacts existants sans les déplacer. Les équipements visibles peuvent être identifiés automatiquement par le modèle vision, puis chacun suit exactement les mêmes étapes, quel que soit son type.

~~~json
{
  "schema": 1,
  "id": "couronne_nouvelle_unite",
  "name": "Nouvelle unité de la Couronne",
  "source": {"character_image": "assets/concepts/couronne/units/nouvelle_unite.png"}
}
~~~

Le résultat final est **assets/experiments/units/<id>/manifest.json** : références des PNG/GLB, descriptions et prises des équipements, tailles estimées et état validé de chaque étape. Ce manifeste n'est émis qu'après intégration locale réussie.

~~~bash
python scripts/unit-pipeline.py list
python scripts/unit-pipeline.py status --unit marches_hache
python scripts/unit-pipeline.py status --unit marches_hache --json
python scripts/unit-pipeline.py run --unit marches_hache --dry-run
python scripts/unit-pipeline.py run --unit marches_hache
~~~

Les résultats déjà présents sont réutilisés. Le pipeline vérifie l'en-tête des GLB, les PNG et les JSON ; la dernière étape construit et valide un bundle local du Character Lab dans un dossier temporaire, sans le publier.

## Étapes individuelles

| Sélecteur | Résultat | Exécution |
|---|---|---|
| source | Illustration initiale avec objet | Entrée de référence |
| equipment_identify | Équipements et descriptions fondées sur la fiche originale | Modèle vision, une réponse mémorisée |
| turnaround | Face, dos, gauche, droite | Muse, appel payant si manquant |
| body | GLB texturé | fal.ai, appel payant si manquant |
| rig | GLB avec squelette | Uthana, appel payant si manquant |
| animations | GLB jouable avec Mixamo | Conversion / retargeting local |
| object_source | Illustration isolée de chaque équipement identifié | Muse, appel payant si manquant |
| object_mesh | GLB indépendant de chaque équipement | TRELLIS, appel payant si manquant |
| object_size | Estimation de la longueur en cm | Gemini 2.5 Flash-Lite, appel payant si manquant |
| object_grip | Main, prise et orientation | Vision Flash-Lite, appel payant si manquant |
| object_landmarks | Sommets de prise, tête et **vrai tranchant** du GLB | Quatre vues du GLB + vision Flash-Lite, repères 3D enregistrés dans le plan canonique |
| integrate | Bundle 3D local et catalogue | Gratuit, hors ligne |

~~~bash
python scripts/unit-pipeline.py run --unit marches_hache --stage integrate
python scripts/unit-pipeline.py run --unit couronne_archer --stage equipment_identify --dry-run
python scripts/unit-pipeline.py run --unit marches_hache --stage object_size --dry-run
python scripts/unit-pipeline.py bootstrap --unit marches_hache --stage object_size
python scripts/unit-pipeline.py run --unit marches_hache --stage object_size --allow-paid
python scripts/unit-pipeline.py run --unit marches_hache --stage object_landmarks --allow-paid
~~~

Les étapes potentiellement payantes sont bloquées par défaut lorsqu'un résultat manque. L'option --allow-paid doit être fournie explicitement. Les résultats et reçus sont conservés pour éviter les soumissions répétées, y compris les résultats dont l'issue est incertaine. Une requête incertaine bloque la reprise automatique plutôt que de doubler le coût. Le pipeline réutilise les artéfacts existants quand ils sont présents et valides.

Les credentials restent exclusivement dans des variables d'environnement : OPENROUTER_API_KEY, OPENROUTER_IMAGE_MODEL, FAL_KEY ou FAL_API_KEY, REPLICATE_API_TOKEN. Aucun secret dans la fiche JSON. La commande bootstrap prépare les dépendances de l'étape sélectionnée seulement si des fichiers sont manquants.

## GitHub Actions est un lanceur, pas le pipeline

Le workflow **.github/workflows/unit-pipeline.yml** expose le choix unit, stage et allow_paid, puis invoque exactement le même script. Ses exécutions automatiques lors de modifications du pipeline se limitent aux tests gratuits et à l'assemblage local. En lancement manuel, il peut sauvegarder les fichiers et reçus produits sur main.

Les anciens workflows spécialisés sont conservés comme archive et compatibilité ; le pipeline principal ne les appelle pas. Le code projet construit les requêtes et appelle directement les outils génériques pour toute unité sélectionnée. Les checkpoints d'identification d'équipement, de génération et de dimensions sont également sauvegardés par le workflow.

## Ajouter une autre unité

Créer une fiche JSON minimale de l'unité avec le chemin de son image originale. Lancer `python scripts/unit-pipeline.py run --unit <id> --dry-run` pour voir les étapes, ou `--allow-paid` pour autoriser celles qui manquent. L'identification automatique écrit une description de chaque équipement, qui sert ensuite de référence à sa génération Muse, à son GLB TRELLIS et à son analyse physique/prise. Il n'existe plus de blocage lié à une liste de personnages ou de noms d'armes dans l'orchestrateur.

**Limite technique explicitée :** le solveur peut utiliser des repères 3D sur un manche (`shaft`), un cadre courbe (`frame`), une poignée aplatie (`flat_handle`) ou une prise sur le corps d'un objet (`body`). Pour une géométrie réellement ambiguë, il refuse de fabriquer une orientation. L'attache de l'arc à une seule main ne dépend ni de la simulation de la corde ni de l'IK de la seconde main. Un véritable tir avec flèche reste une capacité d'animation distincte, jamais prétendue opérationnelle sans son clip.

**Contrat de contact indépendant de l'unité.** `object_landmarks` rend quatre projections du **vrai GLB** de l'objet, demande au petit modèle vision d'y localiser la prise, le bout du manche, la partie active et son tranchant, puis retrouve des positions sur les sommets 3D originaux. Ces positions signées sont écrites dans l'unique `grip-plan.json`, lié au SHA-256 du GLB. Dans le Character Lab, `rig-contact-landmarks.js` trouve paume, index, majeur, auriculaire, poignet, coude, pieds et orteils dans le squelette courant. Le solveur `weapon-grip-geometry.js` oriente le repère de l'objet vers ce repère anatomique, quelle que soit l'unité. Une orientation PCA seule ne peut plus décider de quel côté se trouve le tranchant. Un GLB sans repères validés est refusé : le moteur n'invente plus de rotation de secours.

**Animations indépendantes.** Le contrat de prise reste valable même si le bon geste manque. `equipment-animation-policy.js` associe les catégories d'actions (hache, épée, arc, outil, etc.) à leurs animations Mixamo compatibles et interdit de réutiliser une animation d'attaque incompatible. Tir de corde, seconde main et événements de projectile appartiennent à la couche d'action, et non à l'orientation de la prise.

**GO visuel automatique.** Après création du GLB et des repères, le workflow `prop-visual-qa.yml` appelle les scripts **du projet** `capture-prop-contact.mjs` puis `run-prop-visual-qa.py`. Ils rendent trois vues de chaque unité jouable tenant son objet (plus la vue d'action lorsque disponible), transmettent ces vues au petit modèle vision et exigent un véritable **GO/NO-GO** pour la prise, le tranchant et l'échelle. Le résultat et sa justification sont intégrés à l'unique `grip-plan.json`. Le reçu brut est conservé avant validation; la même configuration ne provoque pas une nouvelle dépense. Un NO-GO empêche de déclarer le test final réussi.

Cette migration conserve les gros GLB et PNG historiques à leur emplacement : pas de génération 3D refacturée et pas de liens de l'arène cassés. Les prises secondaires par IK et la bibliothèque exhaustive d'animations d'objets restent des fonctions indépendantes du montage rigide générique.

## Validation

- scripts/test-unit-pipeline.py : sélection, contrôles de fichiers, absence de dépenses implicites.
- scripts/test-prop-mesh-landmarks.py : rendu des vrais GLB et projection signée vision → sommets.
- scripts/test-rig-contact-landmarks.mjs : transfert d'une prise entre deux squelettes non identiques.
- scripts/test-verify-prop-visual-qa.py : vérification du contrat de verdict vision GO/NO-GO.
- scripts/unit-pipeline.py : assemblage et vérification du catalogue Character Lab.
- scripts/build-character-lab-pages.mjs : construction réutilisable du site statique.
- docs/character-production-pipeline.md : architecture cible multi-objets.
