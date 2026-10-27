# WarConquer — terrain d'essai isométrique (Character Lab)

## Ouvrir la plateforme

À la racine du dépôt, avec **Node.js 20+** et un navigateur moderne :

~~~bash
node scripts/serve-character-lab.mjs
~~~

Naviguer ensuite vers **http://127.0.0.1:4173/character-lab.html**. Le serveur écoute uniquement sur l'ordinateur local (127.0.0.1), sans dépendance npm ni service payant. Internet est nécessaire au moteur Babylon.js chargé depuis son CDN.

La page est [character-lab.html](../character-lab.html), la logique du terrain [scripts/character-lab-client.js](../scripts/character-lab-client.js), et le serveur/catégoriseur [scripts/serve-character-lab.mjs](../scripts/serve-character-lab.mjs). On peut aussi ouvrir la page comme fichier statique puis importer manuellement un fichier **.glb**, mais cette option ne bénéficie pas de la découverte automatique.

## Contrôles du personnage sur le terrain 3D

| Commande | Résultat |
| --- | --- |
| **W A S D** / flèches | Déplacement continu sur le plan, relatif à la caméra |
| **Shift** | Déplacement plus rapide |
| **Espace** / bouton Attaquer | Déclenche le clip de combat, s'il existe dans le GLB |
| **R** / bouton Replacer | Replace l'unité au centre |
| **Souris** | Orbite et zoom de la caméra |
| **Vue isométrique** | Revient à l'angle de départ et suit le personnage |
| **Rotation 90°** | Corrige l'orientation initiale d'un modèle GLB |
| **Activer/désactiver le suivi** | Fige ou libère la cible de caméra |
| **Pavé WASD à l'écran** | Déplacement tactile/pointeur |

Le déplacement n'utilise pas de sprites : un pivot 3D est déplacé dans une scène Babylon et sa rotation suit la direction du déplacement. L'importeur mesure les bornes mondiales et corrige une orientation horizontale ainsi qu'une unité réduite (cas des rigs Uthana à armature centimétrique).

## Ce qui est réellement disponible au 27 octobre 2026

- **Images source** : concept initial plus quatre références T-pose face, dos, gauche et droite du guerrier à la hache des Marches.
- **Maillage** : unrigged.glb, construit par Hunyuan3D-2mv, 25 000 triangles.
- **Squelette** : rigged.glb, avec 52 articulations auto-riggées.
- **Animation d'attaque** : axe-chop-v1/warconquer-animated.glb, retargeté, sélectionné par défaut.
- **Déplacement WASD** : implémenté sur un terrain isométrique, avec caméra et attaque déclenchable.
- **Marche/course réelle des jambes** : **pas encore produite**. Sans un clip Walk/Run/Marche, le personnage se déplace spatialement (il glisse) ; la plateforme l'annonce clairement.
- **Texture du corps** : le GLB initial reste sans texture. Un atlas UV projeté depuis les quatre vues est en cours de construction avec la bibliothèque de mouvements Mixamo ; la qualité doit être évaluée visuellement.
- **Arme physique indépendante** : `assets/experiments/props/marches_hache/trellis-v1/axe.glb` est un **vrai modèle TRELLIS texturé** (~1,36 Mo), reconstruit depuis `assets/concepts/marches/objects/hache_arme.png` via une prédiction Replicate unique. Le labo tente de l'attacher au nœud de main droite des rigs GLB ; prise, position et rotation sont expérimentales. La capture du terrain permettra de vérifier visuellement l'ensemble.
- **Animations réelles** : un pipeline séparé importe les FBX Mixamo existants `Standing_Idle_3`, `Standing_Walk_Forward_3`, `Standing_Run_Forward_3` et `Standing_Melee_Attack_Downward`, puis les retargete sur le rig du guerrier ; son artefact n'est pas déclaré disponible tant que le workflow n'a pas fini et les clips n'ont pas été vérifiés.

L'objectif de ce labo est de voir les limites du résultat en situation de jeu avant d'engager d'autres dépenses. La page ne génère aucune animation et ne déclenche aucun appel à Replicate ou OpenRouter.

## Compatibilité du catalogue

Le serveur découvre automatiquement la hiérarchie :

~~~text
assets/experiments/rig-ready-3d/<unit>/<pose>/
  unrigged.glb
  rigged.glb
  motion/<clip>/warconquer-animated.glb
  motion/<clip>/warconquer-playable.glb    # optionnel : plusieurs clips réunis
~~~

GET /api/character-lab fournit les modèles découverts, les références et les métriques connues. Un modèle futur ne nécessite donc pas de modifier la liste codée en dur. Le fichier peut aussi être importé par glisser-déposer sur le terrain.

Pour une animation de déplacement réelle, le prochain jalon est de générer puis transférer une boucle de marche sur **le même squelette Mixamo** que le guerrier riggé. Le labo activera automatiquement un groupe d'animation nommé Walk, Run ou Marche (nom de clip distinct du nom de faction). La caméra démarre cadrée près du personnage pour inspecter les détails. Il faudra alors vérifier les pieds (absence de glissement, déformation, contacts), le passage marche/arrêt et le combat. Une boucle de marche et une attaque en deux fichiers ne deviennent pas spontanément un seul modèle multi-clips.

## Tests

- **WebSuite** rend automatiquement [character-lab.html](../character-lab.html) après une modification HTML sur main.
- Le workflow [Character Lab QA](../.github/workflows/character-lab-qa.yml) vérifie le serveur, l'accès aux fichiers réels, les quatre vues, l'en-tête GLB, le JavaScript et capture une image du terrain 3D dans [assets/experiments/character-lab-qa/terrain-live.png](../assets/experiments/character-lab-qa/terrain-live.png).
- Ce test ne fait aucun appel de génération payant. Il est déclenché une fois par la création/modification de ce document ou manuellement dans GitHub Actions.

Une capture valide **n'est pas encore** une vérification humaine des animations : il faut tester les commandes et la marche dans le navigateur.
