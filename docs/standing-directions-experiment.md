# Expérience — 8 vues immobiles, homme de hache des Marches

Un personnage WarConquer existant, huit images **fixes**. Une image par direction : N, NE, E, SE, S, SW, W, NW. Aucun cycle de marche, aucun mouvement, aucune vidéo, aucun pixel art.

Chaque image est générée par OpenRouter/Muse à partir de `assets/concepts/marches/units/hache.png`, avec contrainte de posture immobile, même équipement tenu du même côté anatomique, caméra RTS légèrement plongeante. Résolution de sortie 1024 × 1024 pixels, PNG transparent, pieds à ligne de base commune. Le contact-sheet rassemble huit sorties dans un ordre N→NW.

Pipeline : `standing-directions-request.json` → `.github/workflows/generate-standing-directions.yml` → `scripts/generate-standing-directions.py` → `assets/experiments/standing-turnaround/marches_hache/`.

Les images sont des **brouillons à vérifier par le propriétaire du projet**; ni le succès Actions ni l'analyse alpha ne prouvent le respect de la direction ou l'identité des équipements. En cas d'échec partiel, conserver les réussites et les originaux bruts temporairement dans un artefact Actions; ne pas effectuer de nouvelle génération payante automatiquement.
