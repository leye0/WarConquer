# WarConquer — mouvements Mixamo existants pour le guerrier à la hache

## Source trouvée

- Catalogue original : https://www.mixamo.com/
- Miroir de recherche des animations : https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters
- Dossier de clips FBX sans géométrie : `animation_motion/` (2 317 clips réels, ~65 os Mixamo, 30 FPS).
- Export avec personnage témoin Y Bot pour prévisualisation : `animation_motion_ybot/`.
- Licence du miroir : `adobe-mixamo-terms`, **pas CC0**. Avant distribution du jeu, utiliser des assets dûment obtenus via Mixamo, et ne pas distribuer un paquet d'animations FBX brutes comme bibliothèque autonome.

## Clips choisis — tous « with axe »

| Fonction | Fichier de la bibliothèque | Frames à 30 FPS | ID du mouvement Mixamo |
| --- | --- | ---: | --- |
| Idle armé | `Standing_Idle_3.fbx` | 56 | `c9ced017-b96c-11e4-a802-0aaa78deedf9` |
| Marche en avant | `Standing_Walk_Forward_3.fbx` | 41 | `c9cee62c-b96c-11e4-a802-0aaa78deedf9` |
| Course en avant | `Standing_Run_Forward_3.fbx` | 23 | `c9cee049-b96c-11e4-a802-0aaa78deedf9` |
| Coup descendant | `Standing_Melee_Attack_Downward.fbx` | 107 | `c9ced340-b96c-11e4-a802-0aaa78deedf9` |
| Coupe horizontale (alternative) | `Standing_Melee_Attack_Horizontal.fbx` | 171 | `c9ced411-b96c-11e4-a802-0aaa78deedf9` |

URL directe d'un fichier (remplacer `CLIP`) :
`https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters/resolve/main/animation_motion/CLIP.fbx`

Exemple : https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters/resolve/main/animation_motion/Standing_Walk_Forward_3.fbx

Catalogue et descriptions observés :
- https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters/viewer/animations/train?p=19
- https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters/viewer/animations/train?p=20

## Intégration technique restante

1. Obtenir les FBX légitimement. Le miroir de recherche fournit un index exploitable, mais WarConquer n'embarque pas encore ces fichiers.
2. Convertir FBX vers glTF/GLB hors-ligne (Blender par exemple). Ne pas substituer Y Bot à notre guerrier.
3. Retargeter les rotations du squelette Mixamo de 65 articulations vers les 52 os réellement présents sur le GLB WarConquer; aligner poses de repos et axes. Conserver la peau, la géométrie et les poids du rig existant. Neutraliser la translation globale des clips locomotion si WASD gère le déplacement.
4. Réunir Idle, Walk, Run et Attack comme **quatre vrais clips distincts** dans un GLB jouable.
5. Tester la pose des bras, les pieds, les boucles et l'attaque dans Character Lab (WASD, Shift, Espace), puis inspecter une capture vidéo/les poses.
6. Appliquer séparément une texture UV aux quatre vues sources; ce travail n'est pas effectué par les fichiers de mouvement.

Le coup de hache actuellement présent est issu d'`uthana/text-to-motion-diffusion-v2`, sur un squelette UE5 Manny, généré avec le prompt de `scripts/generate-rig-ready-motion.py`, puis transféré sur notre squelette Mixamo. Ce n'est pas un clip Mixamo et sa qualité visuelle n'est pas approuvée.

**État : fichiers Mixamo réels identifiés en ligne; pas encore téléchargés, retargetés ni testés sur WarConquer.** Aucun cycle de marche/course procédural n'est requis.
