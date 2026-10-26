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

Grunt -> homme de hache des Marches, haute résolution. La page source annonce 380x631 pixels. Après inspection de la planche originale, la zone supérieure de **274 px** correspond à **5 colonnes d'orientations et 5 rangées de phases de marche**. Le temps descend verticalement dans chaque colonne. Ne pas inférer une structure 8x8 arbitraire.

Le pipeline télécharge l'image Warcraft II de manière temporaire (artefact debug seulement), puis demande à Muse une planche originale de 25 poses 5x5 en se référant aussi au concept PNG WarConquer.

Fichiers : sprite-sheet-request.json, scripts/generate-sprite-sheet.py, .github/workflows/generate-sprite-sheet.yml. Sorties candidates : assets/spritesheets/drafts/*.png avec PNG de contrôle et métadonnées.

Statut : **brouillon, pas d'approbation automatique**. Le premier essai Muse a rendu 20 cases (4 phases × 5 directions) plutôt que les 25 voulues. Vérifier une par une les cases : nombre exact, identité constante, posture et angle, équipement, cadrage, contact au sol, détourage, peinture haute résolution. Des statistiques alpha ne prouvent pas ces propriétés. Un seul appel Muse par exécution ; pas de retry payant.

Si un modèle ne préserve pas la grille entière, passer à des groupes de poses plus petits (ex. une rangée par appel) puis assembler de manière déterministe avec Pillow, jamais fabriquer des mannequins SVG comme finalité.

## État réel du pilote — 26 octobre 2026

- [Premier run 40355710178](https://github.com/leye0/WarConquer/actions/runs/40355710178) : échec de téléchargement direct depuis Spriters Resource (HTTP 403), **aucun appel Muse**.
- Source de remplacement : miroir GitHub public `DevCrumbs/Warcraft-II` (exactement le fichier PNG Grunt, blob SHA-1 `6ce7fdfb4d68c401782149df83d02414389736c5`), accessible aux runners GitHub, sans copie des pixels originaux dans le dépôt privé WarConquer.
- [Run 40357564315](https://github.com/leye0/WarConquer/actions/runs/40357564315) : référence téléchargée, erreur fournisseur **OpenRouter 502**, aucune image produite.
- [Run Muse réussi 40358268004](https://github.com/leye0/WarConquer/actions/runs/40358268004) : réponse Muse 1600×1600 à fond noir contenant **4 rangées × 5 colonnes**, personnages WarConquer originaux et détaillés; coût indiqué dans le rapport d'origine : 0,01 USD.
- Le détourage `rembg` sur fond noir a détruit la quasi-totalité des sprites; la première planche commitée était inutilisable.
- [Run de récupération 40360006858](https://github.com/leye0/WarConquer/actions/runs/40360006858) : récupération du PNG original depuis le premier artefact GitHub Actions, extraction déterministe du fond noir, normalisation des 20 images dans des cases individuelles **448×448**, ancrage cohérent, commit sur `main` **sans nouvel appel payant**.

### Planches à examiner

- [Planche de validation, fond gris avec grille](../assets/spritesheets/drafts/marches_hache_walk_pilot_review.png)
- [Planche de sprites PNG transparent](../assets/spritesheets/drafts/marches_hache_walk_pilot.png)
- [Métadonnées, état et contrôles de couverture](../assets/spritesheets/drafts/marches_hache_walk_pilot.json)

**Ce n'est pas encore validé** : Muse n'a produit que quatre phases sur cinq, les colonnes de direction se ressemblent parfois trop et les jambes ne montrent pas toujours une progression de marche assez marquée. Les sprites ont un bon niveau de détail, mais ils doivent être soumis à une validation visuelle humaine avant d'être considérés comme un template définitif.

### Autres catégories

Les autres planches sont accessibles par le même miroir public GitHub : `Ogre`, `Peon`, `Elven Archer`. Les références ont été retrouvées et inspectées; nous n'avons **pas encore** effectué d'appel Muse pour ces trois catégories. Chaque catégorie exigera une caractérisation propre de son découpage (ne pas supposer que l'archer suit la même géométrie 5×5).
