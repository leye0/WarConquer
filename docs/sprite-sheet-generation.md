# Sprites WarConquer — références d'animation Warcraft II

Objectif : vrais sprites 2D peints et détaillés, en PNG, non pixel art. Ne pas générer de silhouettes SVG.

Le guide Warcraft II fournit UNIQUEMENT la disposition des cases, les poses, les vues et la cinématique. Une deuxième image, notre unité WarConquer, fournit l'identité du sujet, ses vêtements et son style. Aucun original Warcraft II ne doit être enregistré dans le dépôt.

## Spécimens

| Classe | Guide Warcraft II | Unité WarConquer |
| --- | --- | --- |
| Mêlée légère | [Grunt](https://www.spriters-resource.com/ms_dos/warcraftii/asset/29475/) | assets/concepts/marches/units/hache.png |
| Mêlée lourde | [Ogre](https://www.spriters-resource.com/ms_dos/warcraftii/asset/29477/) | assets/concepts/couronne/units/garde_lourd.png |
| Ouvrier | [Peon](https://www.spriters-resource.com/ms_dos/warcraftii/asset/29480/) | assets/concepts/marches/units/paysan.png |
| Archer | [Elven Archer](https://www.spriters-resource.com/ms_dos/warcraftii/asset/29485/) | assets/concepts/couronne/units/archer.png |

## Pilote

Grunt -> homme de hache des Marches, haute résolution. La page source annonce 380x631 pixels. Un essai sur la zone supérieure de 5 rangées et 5 colonnes (287 px de haut) est un **découpage provisoire**. Il faut vérifier visuellement si les rangées et leurs poses correspondent réellement à une séquence de marche avant de l'adopter. Ne pas inférer une structure 8x8 arbitraire.

Le pipeline télécharge l'image Warcraft II de manière temporaire (artefact debug seulement), puis demande à Muse une planche originale de 25 poses 5x5 en se référant aussi au concept PNG WarConquer.

Fichiers : sprite-sheet-request.json, scripts/generate-sprite-sheet.py, .github/workflows/generate-sprite-sheet.yml. Sorties candidates : assets/spritesheets/drafts/*.png avec PNG de contrôle et métadonnées.

Statut : **brouillon, pas d'approbation automatique**. Vérifier une par une 25 cases : nombre exact, identité constante, posture et angle, équipement, cadrage, contact au sol, détourage, peinture haute résolution. Des statistiques alpha ne prouvent pas ces propriétés. Un seul appel Muse par exécution ; pas de retry payant.

Si un modèle ne préserve pas la grille entière, passer à des groupes de poses plus petits (ex. une rangée par appel) puis assembler de manière déterministe avec Pillow, jamais fabriquer des mannequins SVG comme finalité.
