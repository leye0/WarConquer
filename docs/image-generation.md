# Génération de concepts WarConquer avec OpenRouter / Muse

Le modèle est fourni par le secret GitHub `OPENROUTER_IMAGE_MODEL` (actuellement `meta/muse-image`), et l'API par `OPENROUTER_API_KEY`. Le workflow utilise exclusivement le modèle configuré : aucun service ou modèle de secours et aucune nouvelle tentative payante automatique.

## Catalogues

- `docs/visual-asset-catalog.md` : 68 unités, navires et bâtiments.
- `docs/object-asset-catalog.md` : 10 objets narratifs isolés.
- `docs/narrative-asset-catalog.md` : 18 personnages, Huissiers du Minuit et sites de mémoire.

Les descriptions et palettes viennent des bibles narratives. Chaque génération est guidée par des références visuelles existantes du dépôt et comporte ses prompts, références SHA-256, statistiques de transparence et éventuel recadrage dans le JSON voisin.

## Déclencher un lot

Modifier `image-request.json` sur `main` :

```json
{
  "targets": ["assets/concepts/neutral/sites/relais_intact.png"],
  "concurrency": 2
}
```

Une mise à jour de ce fichier déclenche `.github/workflows/generate-image.yml`. Un contrôle `--dry-run` vérifie d'abord les sujets demandés avant tout appel payant.

Les PNG et JSON générés sont ajoutés **directement sur `main`**, y compris les succès partiels si un autre sujet du lot échoue. Aucun processus manuel de branches de révision n'est requis.

Par défaut, un fichier existant est ignoré sans frais. Pour remplacer explicitement une image sélectionnée, ajouter son chemin à `replace_existing` :

```json
{
  "targets": ["assets/concepts/neutral/objects/masque_signataire.png"],
  "replace_existing": ["assets/concepts/neutral/objects/masque_signataire.png"],
  "concurrency": 1
}
```

## Contrôles et transparence

Les sorties opaques sont détourées par `rembg/u2netp`, avec session partagée et modèle mis en cache. Les originaux sont conservés dans `image-output/raw` de l'artefact Actions. La fraction transparente et la présence de foreground opaque sont vérifiées. Ensuite, un ajustement de taille et de position sur fond RGBA vise au moins 15 % de marge sur chaque bord; il ne reconstitue pas une partie du sujet déjà coupée par le modèle. La métadonnée `source_edge_contact` aide à signaler un risque de découpe initiale.

Les journaux indiquent le fichier en cause, le type d'exception, le statut HTTP et un message filtré; les données sensibles sont masquées. `image-output/report.json` et `contact-sheet.png` sont fournis dans l'artefact `generated-images`, même en cas de succès partiel.

La validation du pipeline n'est **pas une approbation visuelle** : vérifier à taille réelle les PNG sur fond clair et sombre, la fidélité aux descriptions et les silhouettes avant de les considérer définitifs.

Test de sélection sans API : `python scripts/generate-image.py --dry-run`.
