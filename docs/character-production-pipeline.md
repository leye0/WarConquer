# WarConquer — chaîne générique de personnages, équipements et gestes

## Contrat de production

Une **fiche d'unité** est la source de vérité : `unit_id`, apparence, faction,
`equipment[]` avec type, rôle et emplacement, `abilities[]`, références
visuelles, provenance des modèles, empreintes SHA et seuils de confiance.
L'avatar, les GLB des équipements, le rig et les animations sont des
**ressources indépendantes**, assemblées de manière reproductible.

| Étape | Entrée | Résultat | Mécanisme |
|---|---|---|---|
| 1. Fiche initiale | Description, illustration | Fiche structurée | Contrôle de cohérence |
| 2. Vues du corps | Illustration | Face, dos, gauche, droite en T/A-pose | Muse/OpenRouter avec contrôles de silhouette |
| 3. Corps texturé | Face/dos/gauche | GLB avec UV/PBR | fal.ai Hunyuan3D multi-view (l'API utilisée n'accepte que **trois** vues ; la droite sert à la QA) |
| 4. Rig | GLB texturé | Squelette articulé | Uthana ; préservation des UV et des matériaux |
| 5. Objets 2D | Chaque objet de la fiche | Un PNG détouré en trois-quarts, tête et poignée visibles | Muse avec style cohérent |
| 6. Objets 3D | Chaque PNG objet | Un GLB indépendant | TRELLIS (génération moins coûteuse que celle du corps) |
| 7. Sémantique | PNG de l'objet **et** personnage | Type, grip, direction, prise main(s), repères normalisés, confiance | Modèle vision sur OpenRouter, réponse JSON versionnée |
| 8. Géométrie | GLB objet + plan vision | Repère local 3D de prise et orientation | PCA, section du manche, géométrie réelle du maillage, refus des cas ambigus |
| 9. Montage | Rig + plan + repères 3D | Accessoire relié au bon os/point anatomique | Matrice de transformation + socket ; IK pour la deuxième main si nécessaire |
| 10. Gestes | `equipment[]`, `abilities[]` | Actions et animations compatibles | Bibliothèque Mixamo indexée par capacités |
| 11. QA | Unité complète | Captures de face/dos/profil, animation, collisions | Tests Chrome + vérification visuelle |

### Séparation sémantique / géométrie

Le LLM vision décide **ce qu'est l'objet et où il devrait être tenu**.
Il n'invente pas un quaternion de rotation GLB. Le solveur dérive les
coordonnées locales de l'objet à partir de son maillage et transforme les
repères vers la main (ou un autre socket) du rig. Un GLB peut avoir un
axe arbitraire. La transformation doit rester valide après rotation du
personnage et pendant l'animation. Les réponses du modèle sont
mémorisées et les ambiguïtés empêchent la fixation silencieuse.

Le contrat existant `grip-plan.json` (schéma 2) traite déjà la hache :
`assets/experiments/props/marches_hache/trellis-v1/grip-plan.json`.
`scripts/weapon-grip-geometry.js` sait reconnaître un manche et
une tête de hache même quand le GLB est retourné ou orienté de biais.
L'analyse vision et le GLB demeurent séparés.

### Sockets et interactions physiques

Une arme n'est pas toujours dans la main droite. L'architecture doit
distinguer les points de montage et les points d'interaction :
`right_hand`, `left_hand`, `left_forearm`, `right_forearm`,
`back`, `hip_left`, `hip_right`, `head`, `chest`,
`two_hand_primary`, `two_hand_secondary`.

Une hache à deux mains se fixe à **une main primaire** et impose une
cible de contact à la main secondaire via IK; l'épaule/coude/poignet
s'adaptent à la poignée sans déformer le manche. Le système actuel
**n'implémente pas encore cette IK** : la hache suit seulement la main
primaire. Un arc demande davantage : une main tient le corps de l'arc,
l'autre tire la corde, une flèche suit l'encoche jusqu'à l'instant
`arrow_release` puis devient projectile. Ces contraintes exigent
un adaptateur spécifique; ce n'est pas équivalent à attacher un GLB
à un os.

### Animations : index par action, pas par nom de fichier

Le fichier `scripts/equipment-animation-policy.js` expose une taxonomie
machine :
- hache → `axe_chop`, frappe descendante, mouvement à deux mains souhaitable;
- épée → `sword_slash` et `sword_thrust`;
- arc → `bow_shot` avec `arrow_release` et IK secondaire;
- arbalète → `crossbow_shot` avec `bolt_release`;
- lance → `spear_thrust`;
- bâton et baguette → `staff_cast`, `wand_cast`;
- bouclier → `shield_block` et plus tard `shield_bash`;
- marteau et outil → `hammer_strike`, `tool_use`;
- dague → `dagger_stab`.

Cette taxonomie contient aussi les **termes de recherche** pour parcourir
la bibliothèque Mixamo. Ce sont des **intentions**, pas des FBX déjà
téléchargés. Un clip n'est « disponible » que si sa véritable animation
a été intégrée et nommée dans le GLB du personnage. Aucun tir à l'arc
n'est simulé avec l'animation de hache.

Les sources FBX Mixamo sont converties dans les runners CI, leurs
mouvements sont transférés avec les `inverseBindMatrices` du rig source,
puis intégrés au GLB final. Ne pas publier une archive libre de fichiers
FBX sous licence Mixamo. Conserver la provenance et les actions
compatibles dans le manifeste de chaque animation.

## Capacité réelle aujourd'hui (27 octobre 2026)

**Existant et testé :** guerrier des Marches en 4 vues, GLB fal.ai texturé,
rig Uthana, huit mouvements Mixamo, hache TRELLIS, premier JSON vision
(Gemini) et solveur PCA d'une prise sur manche, arène mobile.

**En cours / non terminé :** prises sur arcs/boucliers/objets portés,
plusieurs objets équipés simultanément, IK de deuxième main,
liaison avec événements de tirs et de collisions, acquisition et validation
d'une bibliothèque large de gestes. La taxonomie empêche de présenter
ces fonctions comme opérationnelles sans les mouvements et les
adaptateurs nécessaires.

## Validation automatique

`node scripts/test-equipment-animation-policy.mjs` vérifie que l'attaque
du guerrier correspond à la hache, que le catalogue sait décrire les
catégories futures et qu'un arc ne peut **jamais** jouer par défaut une
attaque à la hache. Le navigateur reste strictement hors de la boucle
des appels payants de vision.

## Prochaines étapes de développement

1. Terminer un vrai contact seconde main via IK pour la hache, avec
   captures de plusieurs moments d'attaque.
2. Construire des adaptateurs `frame` (arc), `forearm` (bouclier),
   `flat_handle` (épée/dague) et `back`/`hip` (objets rangés).
3. Indexer et importer une bibliothèque de mouvements Mixamo avec
   classification des interactions et marqueurs temporels.
4. Déclarer et tester une unité archère : arc, flèche, geste de visée,
   tir réel, position de départ du projectile au moment du lâcher.
5. Valider automatiquement plusieurs types de corps et d'objets,
   leur ajustement visuel, leurs contacts et leurs contraintes physiques.
