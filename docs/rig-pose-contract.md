# WarConquer — contrat géométrique stable des références de rig (v2)

Ce document verrouille la **géométrie et les directions** pour toutes les prochaines générations multivues. Il ne prétend pas rendre un modèle génératif mathématiquement déterministe : les sorties doivent être vérifiées. Les PNG acceptés sont toujours identifiés par SHA-256.

## A. Coordonnées physiques invariantes

- Humain bipède unique, debout, symétrique au repos; même visage, équipement textile, proportions et mensurations dans les quatre vues.
- Repère 3D fixé au corps : +Z vers la tête; +X anatomiquement gauche; -X anatomiquement droite; +Y vers l'avant du personnage.
- **T-pose stricte dans le monde 3D**, quel que soit l'angle de caméra : les deux bras sont alignés sur l'axe X, horizontaux, sans fléchir coudes ni poignets. Les bras **ne changent jamais de pose** pendant que l'on fait tourner la caméra.
- Épaules nivelées, dos droit, tête dans l'axe Z; bassin sans rotation, jambes droites légèrement séparées; bottes au sol à Z=0. Mains ouvertes et vides. Aucune hache, épée, bouclier ou objet attaché au corps. Les armes sont des meshes séparés à rattacher au rig après le skinning.
- Même cadrage, même échelle, même éclairage blanc neutre, même position des pieds; une seule personne complète et fond alpha propre.
- Caméra **orthographique**, à hauteur de poitrine, sans perspective ni inclinaison vers le bas (pas une caméra de RTS).

## B. Projections de la même pose, et non quatre poses inventées

| Vue / champ Hunyuan | Rotation de la caméra | Projection attendue |
|---|---|---|
| front / front_image | Corps face à l'objectif | Visage/poitrine visibles; deux bras dessinent une longue horizontale gauche-droite; mains séparées du tronc |
| back / back_image | Caméra opposée, 180° | Dos visible; bras toujours horizontaux gauche-droite; visage invisible |
| left / left_image | Profil gauche exact, 90° | Nez et bottes orientés vers l'écran gauche; les bras s'étendent en profondeur sur X et sont **fortement raccourcis/majoritairement superposés** dans la projection, sans se rabattre vers l'avant du corps |
| right / right_image | Profil droit exact, 270° | Nez et bottes orientés vers l'écran droit; même foreshortening/superposition des bras; pas de seconde poitrine ni de trois-quarts |

**Interdiction de formulation contradictoire :** ne pas imposer « both arms visibly separated from the torso » pour les vues de profil, car l'orthographie y superpose les bras. Exiger explicitement la séparation visible uniquement dans les vues avant/arrière. Ne pas demander que les bras s'étendent horizontalement *dans l'image* de profil : ils restent horizontaux dans le **monde 3D**, perpendiculaires à la caméra.

## C. Architecture du prompt

1. **Identité fixe** : original WarConquer utilisé uniquement pour texture, visage, vêtement, couleurs et taille. Il ne doit pas imposer la posture de combat de l'image d'origine.
2. **Squelette/pose canonique fixe** : décrire la T-pose dans l'espace 3D et le repère X/Y/Z ci-dessus.
3. **Caméra de cette vue** : une et une seule des quatre spécifications B; pas d'adjectifs vagues de type "slightly side" ou "RTS three-quarter".
4. **Contraintes de sortie** : personnage complet, mains ouvertes, aucune arme, aucune autre personne, pas de texte, transparence et marges cohérentes.
5. **Négatifs spécialisés** : front/back rejettent bras baissés et asymétrie; side rejette frontale/3-4 et bras projetés vers le nez ou vers les bords de l'image.

Les quatre prompts finaux sont produits par concaténation de blocs **versionnés et exacts**, non écrits librement pendant les appels. Leurs SHA-256 sont conservés avec les références et PNG.

## D. Ce qui est réellement reproductible

- Geler le nom du modèle Muse, les valeurs exactes de toutes les requêtes, les images de référence et leur SHA, et sauvegarder les réponses/usage. L'API OpenRouter Images propose un paramètre seed, mais **tous les fournisseurs ne garantissent pas** le même résultat à seed identique. Ne l'envoyer que si l'endpoint du modèle actif l'accepte.
- Geler le modèle Hunyuan3D-2mv **version 71798fbc3c9f7b7097e3bb85496e5a797d8b8f616b550692e7c3e176a8e9e5db**, steps=30, guidance_scale=5, seed=1234, randomize_seed=false, octree_resolution=256, target_face_num=25000. Cela améliore la reproductibilité sans garantir un GLB binaire identique sur tous les GPU.
- Pour le rig Uthana, archiver la version exacte au moment de l'appel, les SHA des GLB entrants/sortants et l'identifiant de prédiction. Aucun seed fiable documenté pour l'auto-rig dans notre intégration.
- Stocker chaque ID de prédiction payant immédiatement, avant de faire la collecte. Une reprise **collecte l'ID existant**; elle ne re-soumet pas un modèle.
- Validation humaine du rendu et contrôle automatique des fichiers avant de considérer le lot réutilisable. Contrôles minimaux : nombres de vues, 1024×1024 RGBA, orientation, cadrage et rapport de largeur des deux profils. Plus tard : vérifier skin/JOINTS_0/WEIGHTS_0 dans le GLB et inspecter les coudes/genoux animés.
- En pratique : **un prompt solide spécifie des invariants; le déterminisme opérationnel vient surtout du versionnement, des seeds acceptées, des empreintes et des validations.**

Références officielles :

- [OpenRouter Images — seed et limites](https://openrouter.ai/docs/api/api-reference/images/generate-an-image)
- [Replicate Hunyuan3D-2mv — schéma d'inputs](https://replicate.com/tencent/hunyuan3d-2mv/api/schema)
- [Uthana auto-rig — T/A pose et skinning](https://replicate.com/uthana/create-character-v1/readme)
