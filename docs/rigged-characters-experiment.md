# WarConquer — personnages 3D animables depuis quatre T-poses

## Principe retenu (2026-10-27)

L'objectif est de remplacer les expérimentations de mouvements 2D isolés par une **source 3D articulable commune**, puis d'appliquer des animations squelettiques et de voir le personnage librement sous n'importe quel angle.

**La pose d'entrée est déterminante :** produire **une stricte T-pose identique** en quatre vues orthographiques (face, dos, profil gauche, profil droit), caméra à hauteur du personnage, avec bras tendus horizontalement, mains ouvertes et vides, jambes droites légèrement écartées, deux pieds posés au même niveau. Ne pas utiliser des images en pose de combat ou avec une arme tenue pour le rigging.

Il faut distinguer la géométrie et le rigging : un GLB Hunyuan3D-2mv n'est pas un personnage animé tant qu'il n'a ni squelette, ni poids de peau, ni mouvement lié au squelette. Les quatre illustrations sont des **références visuelles cohérentes**, pas un certificat de géométrie humaine correcte.

## Phase A — quatre sources propres, une génération par image (implémentée)

- Requête figée : [rig-source-turnaround-request.json](../rig-source-turnaround-request.json).
- Générateur : [scripts/generate-rig-source-turnaround.py](../scripts/generate-rig-source-turnaround.py).
- Action : [.github/workflows/generate-rig-source-turnaround.yml](../.github/workflows/generate-rig-source-turnaround.yml).
- Résultats : [assets/experiments/rig-source-turnaround/marches_hache/tpose-v1/](../assets/experiments/rig-source-turnaround/marches_hache/tpose-v1/) après le premier run.
- Référence d'apparence : [hache.png](../assets/concepts/marches/units/hache.png), sans en copier la pose de combat ni l'arme.
- Fournisseur : **OpenRouter avec Muse**, secrets existants OPENROUTER_API_KEY et OPENROUTER_IMAGE_MODEL.
- Quatre sorties : front.png, back.png, left.png, right.png (PNG RGBA 1024×1024), métadonnées et planche de contrôle.
- La face est créée en premier puis sert de référence pour les trois autres vues. Une seule requête payante par image manquante, jamais de régénération automatique ni de modèle de secours. Arrêt des nouveaux appels si la face ne montre probablement pas les bras horizontaux. Les sorties précédentes sont préservées sur main même en cas d'échec partiel.
- Le contrôle des pixels vérifie transparence, cadrage, largeur de silhouette et cohérence grossière des bras sur les vues frontale/dorsale. Il **ne peut pas** garantir qu'un profil est à 90°, que les doigts sont corrects ou que l'identité est exactement la même.

**Barrière de qualité :** l'agent ou Léon doit ouvrir les **quatre PNG à taille réelle** et la planche, vérifier anatomie, stricte horizontalité des bras, séparation des deux jambes, cohérence des vêtements, épaule/coude/poignet/genou, absence d'armes et proportions. Les vues sont expressément « non approuvées » par défaut. Ne déclencher aucune nouvelle reconstruction payante à partir d'elles avant cette revue.

## Phase B — maillage 3D (exécutée sur les vues T-pose v2)

Le pipeline automatique [scripts/build-rig-ready-3d.py](../scripts/build-rig-ready-3d.py) et [sa GitHub Action](../.github/workflows/build-rig-ready-3d.yml) attendent le fichier de validation explicite rig-ready-3d-request.json contenant les SHA-256 des quatre images acceptées. Sans cette validation, aucun appel Hunyuan ou Uthana n'est lancé. Il envoie ensuite les quatre images dans les champs Replicate Hunyuan3D-2mv : front_image, back_image, left_image, right_image. Conserver un identifiant de prédiction et une empreinte des images avant toute reprise, ne jamais payer deux fois pour la même tentative; conserver GLB, paramètres, rapport de géométrie, aperçu de rotation.

## Phase C — auto-rig bipède (exécutée et contrôlée structurellement)

[Uthana create-character-v1 sur Replicate](https://replicate.com/uthana/create-character-v1) accepte le GLB non riggé via character_file avec auto_rig=true, front_facing=true et renvoie un personnage articulé GLB/FBX. C'est automatisable par API et conçu pour les meshes humanoïdes en T/A-pose, à condition que le maillage soit réellement humain et exploitable. Coût affiché à la vérification : environ **0,20 USD/sortie** (tarif non contractuel). Séparer rig et arme pour éviter que la hache soit identifiée comme un membre. Vérifier les joints et les poids : un appel réussi ne prouve pas la qualité des déformations.

## Phase D — mouvement du personnage 3D (premier mouvement retargeté)

Uthana text-to-motion-vqvae-v1/diffusion-v2 sur Replicate génère des mouvements sur un **squelette bipède standard**, pas directement sur le rig WarConquer. Il faut **retargeter** les animations et contrôler la correspondance des os, la pose de repos, la main qui tient l'arme, les contacts au sol. Pour les coups de hache/épée, créer ensuite une arme 3D distincte attachée à la main droite, et vérifier le mouvement de l'objet.

Livrables finaux visés : un personnage GLB avec maillage, peau et os; des animations squelettiques séparées (idle, marche/course, attaques); une visionneuse 3D interactive dans laquelle on peut tourner librement autour du personnage et lire les animations.

## État et règles de dépenses

- **Phase A :** les quatre images T-pose v2 ont été produites et examinées. Le profil latéral a été corrigé pour respecter une vraie projection orthographique, et le contrat est dans `docs/rig-pose-contract.md`.
- **Phase B :** une prédiction Hunyuan3D-2mv a produit le GLB non skinné (25 000 triangles). Le maillage reste non texturé.
- **Phase C :** une prédiction Uthana auto-rig a produit 52 os Mixamo avec attributs `JOINTS_0`/`WEIGHTS_0`, et un GLB riggé. La pose de repos a ensuite été vérifiée par skinning logiciel (erreur maximale `0.000001` unité sur les vertices).
- **Phase D :** une prédiction Uthana Diffusion v2 a produit un coup de hache abstrait d'environ 3,92 s sur le rig UE5 Manny; transfert hors-ligne explicite vers les 52 articulations Mixamo, 95 frames et 52 canaux de rotation. Le rendu de 5 poses face/profil fonctionne, mais **n'est pas encore un mouvement de hache utilisable en jeu** : les mains ne tiennent pas ensemble une vraie arme, la véritable arme 3D et les textures ne sont pas disponibles.
- Les Actions de validation, prévisualisation et transfert n'appellent plus de modèle payant. Les seules générations payantes sont à usage unique, sauvegardées par identifiant de prédiction avant polling.
- Aucune branche de révision nouvelle. Ne pas toucher aux sprites et guides historiques, à leurs archives ou à leurs fichiers de contrôle.
- Appels d'image : OpenRouter/Muse seulement. Les étapes de 3D et rigging sont des appels Replicate distincts, gardés derrière leur propre limite et leur propre état.
- Préserver les images brutes échouées en artefact GitHub Actions, les PNG utilisables et les rapports sur main.
- En cas d'appel accepté mais de résultat incertain, ne pas relancer automatiquement. Les sorties API temporaires doivent être téléchargées et conservées rapidement.

## Contrat canonique v2

La [spécification de pose/caméras](rig-pose-contract.md) supprime une contradiction du premier prompt : de profil, les bras restent étendus dans le monde 3D, mais se superposent dans la projection. Le script [generate-rig-profiles-v2.py](../scripts/generate-rig-profiles-v2.py) expérimente des profils propres sans regénérer les faces approuvées; entrées verrouillées par SHA et prompts conservés dans les métadonnées. Les résultats v1 restent archivés pour comparaison.

## Résultats du pilote « Marches — hache » (27 octobre 2026)

La version canonique est `tpose-v2`, basée sur quatre vues dont les empreintes sont figées dans [rig-ready-3d-request.json](../rig-ready-3d-request.json).

| Phase | Fichier vérifiable | Workflow |
|---|---|---|
| Source | [Contact sheet T-pose v2](../assets/experiments/rig-source-turnaround/marches_hache/tpose-v2/review-v2.png) | [Génération Muse](../.github/workflows/generate-rig-source-turnaround.yml) |
| Mesh | [unrigged.glb](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/unrigged.glb) | [Hunyuan3D et Uthana](../.github/workflows/build-rig-ready-3d.yml) |
| Rig | [rigged.glb](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/rigged.glb), [rig-report.json](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/rig-report.json) | Idem |
| Motion source | [source-motion.glb](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/source-motion.glb) | [Animation Uthana, une prédiction](../.github/workflows/generate-rig-ready-motion.yml) |
| Transfert | [warconquer-animated.glb](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/warconquer-animated.glb), [retarget-report.json](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/retarget-report.json) | [Retarget UE5 → Mixamo](../.github/workflows/retarget-rig-ready-motion.yml) |
| Déformation réelle | [Cinq poses face/profil](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/animated-five-frames-front-side.png), [rapport](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/axe-chop-v1/animation-visual-qa.json) | [Visualisation CPU gratuite](../.github/workflows/preview-rig-ready-motion.yml) |

Le [contrat du mouvement](../rig-ready-motion-request.json) contient modèle, version conservée dans `prediction.json`, seed `20261027`, prompt canonique et SHA du rig; une tentative payante maximum, sans retry automatique. La génération coûte approximativement 0,50 USD selon le tarif Replicate vu pendant cet essai. La sortie source est un rig UE5 Manny `pelvis/spine_01/upperarm_l`, tandis que l'auto-rig du personnage produit des noms Mixamo `mixamorig:Hips/...LeftArm`. L'outil de transfert applique une carte explicite pour **52 os**, puis des rotations relatives à la pose de repos dans l'espace mondial; il ne recopie pas aveuglément les quaternions ni les noms de nœuds. La translation du bassin est écartée intentionnellement pour un clip d'attaque sur place.

**Assurance qualité :** le schéma glTF et les poids sont valides, le clip contient des rotations, la pose de repos est numériquement stable, et aucun sommet n'explose dans les cinq échantillons. Le pilote est **encore en attente d'approbation artistique** : il ne prouve ni une vraie prise à deux mains ni une animation de hache réaliste. Les futures étapes sont : préciser ou contraindre la prise de l'arme, texturer le mesh, attacher une hache au squelette, faire un aperçu en mouvement continu, puis ajouter idle/marche/course/attaques et la lecture en continu dans une visionneuse 3D.

**Reproductibilité ≠ identité pixel parfaite :** versions, paramètres, prompts et empreintes d'entrée sont sauvegardés; les sorties génératives, surtout OpenRouter/Muse, ne promettent pas une égalité binaire à chaque nouvelle exécution. Le caractère déterministe du pipeline est principalement garanti par la réutilisation d'artefacts déjà validés, les SHA et l'absence de régénérations implicites.
