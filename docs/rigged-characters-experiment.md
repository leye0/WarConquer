# WarConquer — personnages 3D animables depuis quatre T-poses

## Principe retenu (2026-10-27)

L'objectif est de remplacer les expérimentations de mouvements 2D isolés par une **source 3D articulable commune**, puis d'en dériver toutes les animations et les huit directions de caméra sans redessiner l'identité à chaque vue.

**La pose d'entrée est déterminante :** produire **une stricte T-pose identique** en quatre vues orthographiques (face, dos, profil gauche, profil droit), caméra à hauteur du personnage, avec bras tendus horizontalement, mains ouvertes et vides, jambes droites légèrement écartées, deux pieds posés au même niveau. Ne pas réutiliser comme entrée de rigging les huit vues RTS historiques avec hache tenue ou les images d'attaque.

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

## Phase B — maillage 3D (pipeline implémenté, exécution après acceptation des sources)

Le pipeline automatique [scripts/build-rig-ready-3d.py](../scripts/build-rig-ready-3d.py) et [sa GitHub Action](../.github/workflows/build-rig-ready-3d.yml) attendent le fichier de validation explicite rig-ready-3d-request.json contenant les SHA-256 des quatre images acceptées. Sans cette validation, aucun appel Hunyuan ou Uthana n'est lancé. Il envoie ensuite les quatre images dans les champs Replicate Hunyuan3D-2mv : front_image, back_image, left_image, right_image. Conserver un identifiant de prédiction et une empreinte des images avant toute reprise, ne jamais payer deux fois pour la même tentative; conserver GLB, paramètres, rapport de géométrie, aperçu de rotation.

Il existe **un autre pilote distinct** dans [scripts/build-multiview-3d.py](../scripts/build-multiview-3d.py) qui utilise encore les anciennes vues de personnage debout avec hache. Ne pas confondre ses éventuels résultats avec ce pilote T-pose. Garder historique, coûts et sources séparés.

## Phase C — auto-rig bipède (intégration API implémentée, exécution après maillage)

[Uthana create-character-v1 sur Replicate](https://replicate.com/uthana/create-character-v1) accepte le GLB non riggé via character_file avec auto_rig=true, front_facing=true et renvoie un personnage articulé GLB/FBX. C'est automatisable par API et conçu pour les meshes humanoïdes en T/A-pose, à condition que le maillage soit réellement humain et exploitable. Coût affiché à la vérification : environ **0,20 USD/sortie** (tarif non contractuel). Séparer rig et arme pour éviter que la hache soit identifiée comme un membre. Vérifier les joints et les poids : un appel réussi ne prouve pas la qualité des déformations.

## Phase D — mouvement et huit directions (à tester après rig)

Uthana text-to-motion-vqvae-v1/diffusion-v2 sur Replicate génère des mouvements sur un **squelette bipède standard**, pas directement sur le rig WarConquer. Il faut **retargeter** les animations et contrôler la correspondance des os, la pose de repos, la main qui tient l'arme, les contacts au sol. Pour les coups de hache/épée, créer ensuite une arme 3D distincte attachée à la main droite, et vérifier le mouvement de l'objet.

Livrables finaux visés : rigged-character.glb avec peau et os; animations séparées (idle, walk/run, axe/sword attack); aperçu articulé complet et rendus RTS à huit directions avec camera fixe (N, NE, E, SE, S, SW, W, NW). Des sprites transparents 2D peuvent ensuite être rendus à partir de la même scène 3D si le jeu ne consomme pas directement le GLB.

## État et règles de dépenses

- **Phase A : code/Action ajoutés sur main; résultats et vraie inspection à vérifier dans l'exécution.**
- **Phases B–C T-pose : scripts et workflow de reconstruction/rigging prêts, non exécutés tant que la qualité des quatre vues v2 n'a pas été vérifiée.** Phase D (mouvements et retargeting) reste à connecter après inspection du rig. Ne pas annoncer que le personnage est déjà riggé ou animé.
- Aucune branche de révision nouvelle. Ne pas toucher aux sprites et guides historiques, à leurs archives ou à leurs fichiers de contrôle.
- Appels d'image : OpenRouter/Muse seulement. Les étapes de 3D et rigging sont des appels Replicate distincts, gardés derrière leur propre limite et leur propre état.
- Préserver les images brutes échouées en artefact GitHub Actions, les PNG utilisables et les rapports sur main.
- En cas d'appel accepté mais de résultat incertain, ne pas relancer automatiquement. Les sorties API temporaires doivent être téléchargées et conservées rapidement.

## Contrat canonique v2

La [spécification de pose/caméras](rig-pose-contract.md) supprime une contradiction du premier prompt : de profil, les bras restent étendus dans le monde 3D, mais se superposent dans la projection. Le script [generate-rig-profiles-v2.py](../scripts/generate-rig-profiles-v2.py) expérimente des profils propres sans regénérer les faces approuvées; entrées verrouillées par SHA et prompts conservés dans les métadonnées. Les résultats v1 restent archivés pour comparaison.
