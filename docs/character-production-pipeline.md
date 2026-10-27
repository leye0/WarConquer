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


## Identité des objets : conserver le contexte depuis la génération

**La description initiale de l'objet est une donnée métier, pas un simple prompt jetable.** Dans le pipeline actuel, elle figure dans `axe-image-request.json` : hache forestière utilitaire à deux mains, manche de chêne, une seule tête en fer, proportions crédibles. Elle a servi à générer `hache_arme.png`, en prenant `hache.png` comme référence du porteur.

Le pipeline v3 `scripts/plan-prop-attachment-v3.py` retrouve automatiquement le brief d'origine via `grip-request-v3.json`, en vérifie la provenance (même image de sortie, référence du personnage, SHA-256 du brief/des images/du GLB) et envoie **le brief intégral** avec l'illustration de l'objet et le concept du porteur au LLM vision. Les points de prise et l'orientation demeurent calculés, et le solveur géométrique donne les vraies coordonnées du GLB.

**Le brief ne donne cependant aucune longueur physique explicite.** Dans cette expérience, Gemini a de nouveau proposé **1,10× la hauteur du porteur**, même lorsqu'il avait la description d'origine : preuve que la continuité de contexte ne suffit pas à garantir l'échelle. On conserve son résultat v3, mais **on ne le déploie pas automatiquement** : le champ `visual_qa.status` doit valoir `approved` après comparaison indépendante entre l'illustration de l'unité et le rendu 3D équipé. La v2 reste active jusque-là. Ni bornage arbitraire à 80 %, ni réduction silencieuse sans preuve géométrique.

À terme, la fiche d'unité doit matérialiser dès la **détection des objets sur le personnage** une identité immuable comprenant le type, sa description fonctionnelle, ses parties (manche, tête, tranchant, attaches), les rapports de dimensions visibles, les capacités et la provenance de génération. Les générations 2D/3D et les animations lisent cette identité. Le LLM vision apporte des repères et des validations, pas une nouvelle identité contradictoire.

### Prévention des raccourcis

- Jamais d'estimation d'échelle fondée sur les marges d'une PNG d'objet isolé : celle-ci n'a pas de référentiel physique.
- Une mesure de longueur du même LLM répétée dans deux champs n'est **pas** une validation indépendante.
- Comparer plutôt à l'image du personnage, puis vérifier la main, le diamètre de poignée, les bras et la pose sur un véritable rendu 3D.
- Ne promouvoir une nouvelle prise que si la QA confirme que l'arme est utilisable pendant Idle, marche et attaque.
- Conserver les versions v2/v3 et les réponses payantes intactes. Aucune nouvelle génération 3D n'est nécessaire pour améliorer l'assemblage.

## Réanalyse visuelle à coût réduit sans ancrage (v5)

Le retour d'expérience sur la v4 a révélé un biais explicite : le prompt incluait `CURRENT ACTUAL RENDERED LENGTH/CHARACTER HEIGHT: 1.1` et les spécifications complètes du modèle précédent, dont `length_relative_character_height: 1.1`. L'utilisateur a correctement identifié qu'un modèle pouvait simplement reconfirmer cette valeur fournie.

`scripts/review-prop-in-situ.py` utilise désormais par défaut `google/gemini-2.5-flash-lite` via `grip-render-review-request-v5.json`. L'appel reçoit **la description source et les quatre images**, mais ni la taille 1.1 ni aucune sortie des analyses précédentes. Les captures de l'arène sont recadrées à la scène pour exclure le panneau de statistiques. Un test dédié, `scripts/test-review-prop-unanchored.py`, vérifie l'absence d'ancienne échelle dans le prompt et le retrait du panneau UI des captures. Les plans antérieurs restent accessibles seulement pour la provenance et la comparaison locale **après la réponse**.

Résultat facturé v5 : `0.0004382 USD` (OpenRouter : 1666 tokens entrée, 679 sortie, dont 375 de réflexion). **Malgré l'absence d'ancrage textuel, Flash-Lite a de nouveau proposé 1.1**, avec un diagnostic contradictoire : « manche trop court, à allonger » pour une longueur qui n'évolue pas. La réponse est **conservée en candidate non publiée**, et n'est pas une validation artistique. Aucun GLB n'a été regénéré, aucune prise n'a été automatiquement remplacée. Une meilleure mesure de la silhouette du personnage/objet, ou un autre protocole visuel, sera nécessaire si l'on veut une échelle convaincante.


## Mesure correcte des proportions sur la fiche originale (v6)

La fiche d'origine du guerrier des Marches **montre déjà son arme** : c'est la source principale des proportions. Elle est analysée avec la description originale de l'objet, sans plan vision antérieur ni capture d'une hache agrandie. Les images d'objet isolé servent à identifier la géométrie et la fabrication, **jamais** à donner une échelle physique absolue.

Les essais v2, v3, v4 et v5 ont répété `1.1`, mais les premières analyses étaient ancrées dans leur propre résultat et les rendus déjà dimensionnés. Une autre erreur provenait de la **mesure diagonale du bout de manche jusqu'à la pointe extérieure d'une lame large**. Cette diagonale mélange la longueur utile de l'arme et la largeur de sa tête; elle ne doit pas devenir directement l'échelle uniforme du GLB.

`scripts/measure-prop-scale-blind.py` demande donc des repères distincts sur la fiche source : tête/pieds du porteur, bout du manche, jonction manche/tête, extrémité de la tête **selon l'axe du manche** et pointe de lame **latérale**. Les calculs retournent séparément :
- `shaft_length_ratio` — longueur du manche par rapport au personnage;
- `projected_length_ratio` — longueur projetée manche+tête selon l'axe de l'arme;
- `blade_lateral_extent_ratio` — largeur de la lame hors de cet axe;
- `preferred_length_ratio` — choix du LLM, contrôlé par la mesure projetée.

Le test `scripts/test-measure-prop-scale-blind.py` prouve que déplacer fortement la pointe de la lame **perpendiculairement au manche** ne modifie pas la longueur axiale calculée. [Vérification CI sans appel IA](https://github.com/leye0/WarConquer/actions/runs/40586675639) : réussie. Le premier essai payant v6 a échoué sur une limite OpenRouter HTTP 429, sans nouveau résultat validé; les prises existantes restent actives. Il ne faut pas inventer un nouveau rapport ni présenter les mesures géométriques comme une nouvelle décision du LLM avant une analyse aboutie.
