# Production 3D des unités — exécution locale

Le point d'entrée du pipeline est **scripts/unit-pipeline.py**. Il est propre au projet, peut fonctionner dans un terminal local sans GitHub Actions, et lit une fiche JSON par unité dans **data/units/**.

## Sélectionner une unité

Le premier exemple complet est **data/units/marches_hache.json**. Le format est décrit par **data/schemas/unit-manifest.schema.json** pour aider les éditeurs à valider et compléter les fiches. Il lie la fiche originale 2D, les quatre profils, le corps texturé fal.ai, le squelette Uthana, les mouvements Mixamo et l'illustration, la géométrie, la taille en centimètres et la prise de la hache.

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
| turnaround | Face, dos, gauche, droite | Muse, appel payant si manquant |
| body | GLB texturé | fal.ai, appel payant si manquant |
| rig | GLB avec squelette | Uthana, appel payant si manquant |
| animations | GLB jouable avec Mixamo | Conversion / retargeting local |
| object_source | Illustration isolée de la hache | Muse, appel payant si manquant |
| object_mesh | GLB indépendant de la hache | TRELLIS, appel payant si manquant |
| object_size | Estimation de la longueur en cm | Gemini 2.5 Flash-Lite, appel payant si manquant |
| object_grip | Main, prise et orientation | Vision Flash-Lite, appel payant si manquant |
| integrate | Bundle 3D local et catalogue | Gratuit, hors ligne |

~~~bash
python scripts/unit-pipeline.py run --unit marches_hache --stage integrate
python scripts/unit-pipeline.py run --unit marches_hache --stage object_size --dry-run
python scripts/unit-pipeline.py bootstrap --unit marches_hache --stage object_size
python scripts/unit-pipeline.py run --unit marches_hache --stage object_size --allow-paid
~~~

Les étapes potentiellement payantes sont bloquées par défaut lorsqu'un résultat manque. L'option --allow-paid doit être fournie explicitement. Les scripts d'origine gardent leurs reçus et checkpoints pour éviter les soumissions répétées. Le pipeline ne lance pas lui-même de nouvelles requêtes si les fichiers existent et sont valides.

Les credentials restent exclusivement dans des variables d'environnement : OPENROUTER_API_KEY, OPENROUTER_IMAGE_MODEL, FAL_KEY ou FAL_API_KEY, REPLICATE_API_TOKEN. Aucun secret dans la fiche JSON. La commande bootstrap prépare les dépendances de l'étape sélectionnée seulement si des fichiers sont manquants.

## GitHub Actions est un lanceur, pas le pipeline

Le workflow **.github/workflows/unit-pipeline.yml** expose le choix unit, stage et allow_paid, puis invoque exactement le même script. Ses exécutions automatiques lors de modifications du pipeline se limitent aux tests gratuits et à l'assemblage local. En lancement manuel, il peut sauvegarder les fichiers et reçus produits sur main.

Les anciens workflows spécialisés sont conservés pour compatibilité. Ils ne sont pas nécessaires pour choisir, inspecter, reconstruire les fichiers déjà présents ou assembler le guerrier à partir du CLI. Leur consolidation complète pourra suivre sans casser les artéfacts historiques.

## Ajouter une autre unité

On pourra créer data/units/garde_lourd.json avec ses propres chemins vers images, vues, modèles et objets. Le CLI saura la lister et inspecter les artéfacts. **Limite honnête :** les vieux scripts fal.ai / TRELLIS / Uthana / Muse restent actuellement câblés pour marches_hache. L'adaptateur legacy_marches_hache refuse donc d'exécuter leurs étapes pour une nouvelle unité ; il faudra les paramétrer à partir du manifeste avant d'automatiser une nouvelle unité entièrement.

Cette migration conserve les gros GLB et PNG à leur emplacement : pas de génération 3D refacturée, et pas de liens de l'arène cassés. Les prises secondaires par IK et la bibliothèque exhaustive d'animations d'objets sont encore à réaliser.

## Validation

- scripts/test-unit-pipeline.py : sélection, contrôles de fichiers, absence de dépenses implicites.
- scripts/unit-pipeline.py : assemblage et vérification du catalogue Character Lab.
- scripts/build-character-lab-pages.mjs : construction réutilisable du site statique.
- docs/character-production-pipeline.md : architecture cible multi-objets.
