# Générer une image avec OpenRouter

Dans **Actions → Generate image · OpenRouter → Run workflow**, saisir `prompt`,
`output` et `references` (liste JSON de chemins PNG du dépôt). Les secrets
`OPENROUTER_API_KEY` et `OPENROUTER_IMAGE_MODEL` restent dans GitHub Actions.
Le modèle configuré doit accepter des images de référence via l’API `/api/v1/images`.
Aucun autre modèle n'est substitué automatiquement.

Pour un lot, modifier `image-request.json` avec les chemins du catalogue dans
`targets` et `concurrency` de 1 à 4, puis pousser sur main. Seule la modification
de ce fichier déclenche un lot automatiquement. Un prompt vide au lancement
manuel reprend ce fichier. Les fichiers existants ne sont jamais écrasés.

Chaque requête du catalogue utilise les mêmes deux références de sa faction,
la description officielle et un préambule partagé. Les sorties opaques passent
par rembg/u2netp; les originaux restent dans l’artefact pour contrôler la découpe.
Les coûts rapportés par l’API, prompts, empreintes des références, dimensions et
mesures alpha sont enregistrés dans les fichiers JSON compagnons.
Il n’y a pas de nouvelle tentative payante automatique.

Les candidats sont sauvegardés sur `art/generated-<run>-<attempt>` pour examen,
avec un artefact `generated-images` (PNG, originaux, rapport et planche contact).
Ils ne deviennent pas automatiquement des références approuvées : ouvrir les
images, comparer le style et la palette aux références, inspecter les bords et
la transparence, vérifier les caractéristiques du catalogue avant intégration.
Une planche contact aide à comparer, sans remplacer l’inspection à pleine taille.

Le premier lot est limité à deux soigneurs, un par faction, pour valider la
cohérence avant de générer les sept autres unités manquantes et les 44 navires
et bâtiments. Les 15 images existantes sont conservées.

Test sans API : `python scripts/generate-image.py --dry-run`.
