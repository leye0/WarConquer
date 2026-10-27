# WarConquer — vraie bibliothèque de mouvements Mixamo du guerrier à la hache

## Provenance et droits

- Catalogue : https://www.mixamo.com/
- Miroir de recherche indexé : https://huggingface.co/datasets/Linzhan/Mixamo-Animations-Characters
- 2 317 clips animés, squelette standard Mixamo (~65 os), 30 FPS.
- Archive utilisée dans CI : `animation_motion_ybot/` (FBX d'une animation sur Y Bot, convertible en glTF puis retargetable). Sources temporaires uniquement.
- Licence du miroir : `adobe-mixamo-terms`. Le résultat combine des animations dans un GLB jouable, pas une bibliothèque de FBX bruts. Avant distribution, vérifier la provenance/droits des assets provenant de ce miroir et, si nécessaire, les obtenir depuis Mixamo.

## Quatre fichiers effectivement utilisés (révision du 27 octobre 2026)

| Fonction | Source Mixamo | Description du catalogue | Frames d'origine |
| --- | --- | --- | ---: |
| Idle | `2hand_Idle.fbx` | **Two Handed Weapon Stance** : tenue d'arme tranquille | 144 |
| Walk | `Walking_21.fbx` | **Male Standard Walk** : mouvement des bras naturel | 38 |
| Run | `Run_With_Sword.fbx` | **Running With A Sword In The Right Hand** : locomotion armée | 25 |
| Attack | `Standing_Melee_Attack_Downward.fbx` | **Downward Attack With Axe** | 107 |

Le suffixe `WithAxe` des noms d'animation dans le GLB est un nom de compatibilité d'interface; les sources Idle/Walk/Run ne sont pas toutes des clips explicitement prévus « avec hache ». L'objet TRELLIS est attaché à la main par le navigateur.

Les trois anciennes sources `Standing_Idle_3`, `Standing_Walk_Forward_3`, `Standing_Run_Forward_3` étaient de vrais clips Mixamo, mais inadaptés au résultat souhaité; **elles ont été remplacées**. Leurs métadonnées restent disponibles dans le catalogue Hugging Face; elles ne sont plus incorporées au GLB actif.

## Pipeline réel

1. Télécharger les quatre FBX YBot existants dans `$RUNNER_TEMP` (jamais les publier comme fichiers autonomes).
2. Convertir les FBX en GLB via le binaire Linux précompilé `fbx2gltf@0.9.7-p1`. Blender n'est plus nécessaire en CI.
3. Lire les os de la peau et **inverseBindMatrices** des GLB sources. L'orientation des nœuds exportés correspond souvent à la **première image animée**, pas à la T-pose. La soustraire directement à la première image effaçait toute la position des bras !
4. Calculer chaque mouvement relatif à la *bind pose* de sa source et le transférer en rotations locales sur les 52 os approuvés du guerrier; le déplacement du pivot est géré séparément par WASD.
5. Construire l'atlas UV à partir des PNG T-pose (face, dos, gauche, droite), en respectant l'origine glTF **en haut à gauche** (pas de renversement vertical des UV).
6. Écrire un seul `assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/mixamo-axe-v1/warconquer-playable.glb` contenant texture et quatre clips.
7. Vérifier en Chrome réel via `scripts/test-character-lab-motion.mjs` : Idle, W = Walk, Shift+W = Run, Espace = Attack, avec captures et mouvement du personnage.

La vérification géométrique du résultat et des contacts au sol reste un travail distinct de la présence d'animations dans le conteneur GLB.

## Références du dépôt

- `.github/workflows/build-mixamo-playable.yml`
- `scripts/convert-mixamo-fbx.py`
- `scripts/build-mixamo-playable.py`
- `assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/mixamo-axe-v1/report.json`
- `docs/character-lab.md`

L'ancien coup de hache `axe-chop-v1` dérivait d'une animation générée par Uthana, pas de Mixamo. Il reste disponible pour comparaison mais n'est plus le choix par défaut.
