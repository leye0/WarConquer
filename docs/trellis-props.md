# WarConquer — objets 3D indépendants par TRELLIS v1

## Principe

Les personnages restent issus de Hunyuan3D-2mv (quatre vues), puis sont riggés par Uthana. Les **objets portés**, qui ne nécessitent pas de squelette, utilisent un pipeline à part :

1. Créer ou sélectionner une illustration **d'un seul objet**, détourée, entièrement visible, sans personne ni décor, avec le prompt Muse/OpenRouter existant.
2. Conserver la PNG approuvée et son empreinte SHA-256. La validation des bords alpha est obligatoire : aucun objet coupé.
3. Soumettre **une seule** image à `firtoz/trellis` sur Replicate, version épinglée, avec `images: [fichier_png]`. Un résultat refusé avant attribution d'un identifiant n'est pas une prédiction acceptée.
4. **Sauvegarder l'identifiant de la prédiction** avant d'attendre sa fin pour pouvoir reprendre la collecte sans générer un deuxième objet payant.
5. Télécharger et vérifier le **GLB texturé** (en-tête glTF, maillage, matériaux, images, limite de taille).
6. Importer cet objet GLB comme **prop indépendant** dans Character Lab; attacher à la main droite du squelette dans la scène, sans fusionner l'arme aux sommets du personnage.
7. Corriger visuellement l'échelle, la rotation, la prise et le point de contact du manche. Une vérification glTF réussie ne prouve ni la bonne géométrie ni une prise anatomiquement crédible.

## Premier cas validé : hache des Marches

- Source Muse : `assets/concepts/marches/objects/hache_arme.png` (PNG RGBA 1600 × 1600).
- Requête approuvée et paramètres : `trellis-axe-request.json`.
- Script : `scripts/build-trellis-axe.py` (étapes `validate`, `submit`, `collect`).
- Workflow : `.github/workflows/build-trellis-axe.yml`, lancé automatiquement sur une modification de la requête, du script ou du workflow.
- Modèle : `firtoz/trellis:e8f6c45206993f297372f5436b90350817bd9b4a0d52d2a76df50c1c8afa2b3c`.
- Source SHA-256 : `061c18599da536c363ffa8bb10f648405d31c240f027c3867a46541d2b0d79bc`.
- Identifiant Replicate : `e06j1hzrd5rnc0d1fe8rhvtre8`.
- Résultat : `assets/experiments/props/marches_hache/trellis-v1/axe.glb`, 1 355 836 octets, **1 maillage, 1 matériau, 1 image** intégrée.
- Vérification technique : réussite. Une capture du Character Lab affiche la hache à côté du bras droit; **prise et axe de rotation encore expérimentaux**.
- Prédictions facturables envoyées : **1**. Aucun renouvellement automatique. Coût indicatif Replicate au moment de l'expérience : environ 0,036 USD, variable selon les entrées, et non une valeur confirmée du relevé.

## Séparation des responsabilités

| Étape | Outil | Sortie | Génération payante ? |
| --- | --- | --- | --- |
| Concept de l'objet | Muse / OpenRouter | PNG détourée et approuvée | Oui, une image |
| Objet 3D | Replicate TRELLIS v1 | GLB texturé indépendant | Oui, un appel contrôlé |
| Squelette du guerrier | Uthana | Armature du corps, 52 os | Déjà réalisé |
| Animations du corps | Mixamo, fichiers FBX existants | Idle / Walk / Run / Attack retargetés | Non, clips existants |
| Prise en main | Babylon Character Lab | Transformation liée à `RightHand` | Non |

Le pipeline TRELLIS ci-dessus est **actuellement spécialisé pour la hache des Marches**. Avant de traiter automatiquement les autres objets, généraliser les chemins et la description de la requête sans supprimer les garde-fous SHA, approbation visuelle, budget et identifiant de prédiction. Les FBX Mixamo ont leurs propres modalités de distribution; ne pas les réimporter dans le dépôt en tant que bibliothèque de FBX bruts.
