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
- **Ancienne attaque expérimentale** : axe-chop-v1/warconquer-animated.glb, conservée comme référence. Le **nouveau modèle jouable par défaut** est `motion/mixamo-axe-v1/warconquer-playable.glb` (catalogue local dynamique, priorité 60).
- **Déplacement WASD** : implémenté sur un terrain isométrique, avec caméra et attaque déclenchable.
- **Mouvements réels des jambes** : quatre FBX Mixamo existants (`2hand_Idle`, `Walking_21`, `Run_With_Sword`, `Standing_Melee_Attack_Downward`) ont été convertis par FBX2glTF, puis retargetés sur les **52 os** du personnage. Les groupes `Idle_Mixamo_WithAxe`, `Walk_Mixamo_WithAxe`, `Run_Mixamo_WithAxe` et `Attack_Mixamo_WithAxe` sont enregistrés dans **un même GLB**. Le transfert des rotations repose sur la **vraie bind pose** lue dans les inverseBindMatrices glTF, car les FBX convertis démarrent déjà dans une pose animée; cela évite de soustraire par erreur la position des bras. Le rapport valide des offsets initiaux des bras non proches de la T-pose (Idle 83°/52°, Walk 69°/67°, Run 72°/67°). Le WASD déclenche Walk; Shift déclenche Run; Espace déclenche Attack; l'arrêt déclenche Idle. La qualité visuelle et les contacts au sol restent à vérifier sur captures en mouvement.
- **Texture du corps** : le GLB Mixamo contient déjà un atlas UV PNG intégré, projeté depuis les quatre vues approuvées en respectant la convention glTF (V vers le bas) (25 000 triangles, 75 000 sommets après découpage des UV, image atlas ~982 Ko). Le vieux modèle gris reste accessible. Les coutures et alignements sont **expérimentaux**, en cours de validation visuelle. Le premier essai avait inversé la coordonnée verticale, corrigée le 27 octobre.
- **Arme physique indépendante** : `assets/experiments/props/marches_hache/trellis-v1/axe.glb` est un **vrai modèle TRELLIS texturé** (~1,36 Mo), reconstruit depuis `assets/concepts/marches/objects/hache_arme.png` via une prédiction Replicate unique. Le labo tente de l'attacher au nœud de main droite des rigs GLB ; prise, position et rotation sont expérimentales. La capture du terrain permettra de vérifier visuellement l'ensemble.
- **Workflow Mixamo** : [build-mixamo-playable.yml](../.github/workflows/build-mixamo-playable.yml) a réussi le 27 octobre 2026 ; le fichier combiné et son [rapport](../assets/experiments/rig-ready-3d/marches_hache/tpose-v2/motion/mixamo-axe-v1/report.json) sont sur `main`. Le processus utilise un binaire FBX2glTF précompilé et les sources FBX restent dans l'espace temporaire du runner.

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

Le fichier `warconquer-playable.glb` regroupe maintenant la marche, la course, l'immobilité et l'attaque. Les étapes suivantes sont **des tests visuels**, notamment pieds (glissement, pénétration dans le sol), proportions, coutures de texture, enchaînement marche/arrêt, combat et prise de la hache TRELLIS. La caméra démarre cadrée près du personnage et le moteur offre un contrôle WASD plutôt qu'une lecture automatique.

## Tests

- **WebSuite** rend automatiquement [character-lab.html](../character-lab.html) après une modification HTML sur main.
- Le workflow [Character Lab QA](../.github/workflows/character-lab-qa.yml) vérifie le serveur, l'accès aux fichiers réels, les quatre vues, l'en-tête GLB, le JavaScript et capture une image du terrain 3D dans [assets/experiments/character-lab-qa/terrain-live.png](../assets/experiments/character-lab-qa/terrain-live.png).
- Le test automatisé [test-character-lab-motion.mjs](../scripts/test-character-lab-motion.mjs) lance aussi **Chrome réel par CDP**, maintient les touches **W** puis **Shift+W**, relâche le mouvement, déclenche l'attaque, vérifie les noms du groupe d'animation actif, le déplacement WASD et sauvegarde des captures distinctes (`walk-live.png`, `run-live.png`, `attack-live.png`).
- Ces tests ne font aucun appel de génération payant. Ils se déclenchent avec une modification de ce document ou manuellement dans GitHub Actions.

Une capture valide **n'est pas encore** une vérification humaine des animations : il faut tester les commandes et la marche dans le navigateur.
