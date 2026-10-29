# Contrat générique de manipulation : affordances, état, contacts et contraintes

**Statut : spécification conceptuelle v2 à appliquer au flow, non implémentée intégralement.**  
**Décision : 2026-10-28**  
**Liens :** [plan de validation par poses](held-prop-vision-qa.md) · [contrat technique actuel](../docs/prop-interaction-contract.md).

## La bonne abstraction

Un objet n'est pas simplement « une hache / un pot / un fusil » avec une orientation prédéfinie.

**Interaction = parties sémantiques de l'objet + état et contenu + modalités de contact du personnage + intention de l'action + contraintes spatiales et temporelles + vraie pose Mixamo.**

Exemples critiques :
- Un **pot rempli ouvert**, transporté, a l'obligation de conserver son **ouverture vers le haut** relativement à la gravité, sous peine de déversement. Pour **verser**, une inclinaison contrôlée vers une cible devient au contraire nécessaire.
- Un **pot vide** ne risque pas ce déversement. Un pot **plein mais fermé hermétiquement** peut tolérer une inversion sans fuite selon la règle de jeu. La silhouette seule n'indique pas s'il contient réellement de l'eau ou si le couvercle est étanche.
- Un **fusil** ne cherche pas à rester vertical : sa bouche est une **sortie orientée**, dont l'axe doit pointer vers la cible pendant la visée, tandis que ses contacts peuvent impliquer main principale, support secondaire et appui à l'épaule.
- Une **hache** a un manche pour la prise et un tranchant pour l'action. L'axe du manche, le tranchant et la trajectoire de frappe sont trois choses différentes.
- Un **bouclier** peut être attaché à l'avant-bras par une sangle : exiger que la paume touche un « grip » unique est faux.

Une catégorie (`axe`, `vessel`, `firearm`) sert à exprimer une hypothèse descriptive, **jamais** à générer automatiquement des points, des orientations ou des contacts. Le modèle vision caractérise l'instance réelle, le brief confirme les états non visibles, et le moteur impose les contraintes déclarées.

## Vocabulaire à faire produire au modèle vision

Les termes sont en anglais pour les champs/API, avec un sens stable. **Les IDs de parties sont ouverts** (`axe_cutting_edge`, `pot_opening`, `front_sight`, etc.) : le modèle n'est jamais obligé de choisir la fonction d'un objet selon sa forme.

### 1. Parties et fonctions : `parts[]`

Chaque partie possède `id`, `functional_role`, `region`, `evidence`, `visibility`, `confidence`. Une région est une **boîte/polygone/masque annoté sur l'image**, avec repère de crop; un nom et un point isolé ne suffisent pas.

| `functional_role` | Sens et illustrations |
|---|---|
| `grasp_region` | Endroit où une main **serre** réellement l'objet : manche, poignée, col, garde |
| `support_region` | Endroit qui reçoit une force de soutien sans serrage : dessous d'un pot, fût posé sur la paume |
| `brace_region` | Appui contre une autre partie du corps : crosse à l'épaule, plaque contre l'avant-bras |
| `attachment_region` | Fixation ou suspension : sangle, boucle, crochet, dragonne |
| `active_surface` | Surface qui produit l'effet : tranchant, face du marteau, lame de pelle |
| `active_tip` | Pointe agissante : pointe de lance, pointe de dague |
| `outlet` | Sortie d'un flux ou projectile : bouche du canon, bec verseur, embouchure |
| `opening` / `opening_rim` | Ouverture et bord d'un récipient; la normale **sortante** définit son « dessus » |
| `container_interior` | Volume contenant liquide/objets (possible état de remplissage, pas preuve de contenu) |
| `aiming_reference` | Ligne de visée, mire, axe fonctionnel de projection |
| `shield_front` / `protective_surface` | Face protectrice orientée vers une menace |
| `control_region` | Gâchette, levier, poignée de commande, valve |
| `moving_part` | Partie animée relativement au corps principal : corde, couvercle, détente, charnière |
| `flexible_part` | Élément souple : corde, chaîne, ligne de pêche |
| `hazard_region` | Zone à éviter : flamme, tranchant, pointe, surface brûlante |
| `contact_surface` | Surface de poussée, traction, frottement ou glissement, si distincte des précédentes |

Ce vocabulaire est **multi-étiquette** : la poignée d'une casserole peut être simultanément `grasp_region` et `hazard_region` si elle est brûlante. Une même partie peut participer à plusieurs modes, sans inventer d'autres coordonnées.

### 2. États : `object_state`

Ne pas confondre une caractéristique visible avec un **état réel** ou une règle de gameplay.

| Terme | Valeurs utiles | Qui fait autorité ? |
|---|---|---|
| `contents` | `empty`, `liquid`, `loose_solids`, `solid`, `unknown` | Brief, inventaire/jeu; la vision peut seulement constater un contenu visible |
| `fill_state` | `empty`, `partial`, `full`, `unknown` | État de jeu, jauge, brief |
| `closure_state` | `open`, `covered`, `sealed`, `unknown` | Vision + règle d'étanchéité confirmée |
| `activation_state` | `inactive`, `lit`, `hot`, `loaded`, `tensioned`, `unknown` | État du jeu; non déductible automatiquement de l'apparence |
| `mechanical_behavior` | `rigid`, `articulated`, `flexible`, `unknown` | Asset/physique; un GLB rigide ne suffit pas à simuler une corde |

Tout champ incertain doit avoir `status: "unknown"` et `missing_evidence`. **Ne jamais considérer qu'un pot est rempli, une bouteille hermétique ou un fusil chargé uniquement parce que l'image le suggère.**

### 3. Contacts : `contacts[]`

Un contact n'est pas nécessairement une « main accrochée à un point ».

- `effector` : `left_palm`, `right_palm`, `left_forearm`, `right_forearm`, `shoulder`, `torso`, etc., mappés sur le **vrai rig**, pas sur une convention de caméra.
- `contact_kind` : `grasp` (serrer), `support` (soutenir), `brace` (caler), `strap` (attaché), `hook` (suspendre), `press` (actionner), `release` (relâcher).
- `part_id` : partie visuellement caractérisée et localisée sur le GLB.
- `hand_role` : `primary`, `secondary`, `none`. La main « dominante » n'est pas une propriété universelle de l'objet.
- `contact_window` : début/fin ou événement du clip; le contact peut changer pendant l'action.
- `required` : contact indispensable au mode ou seulement facultatif (avec justification).
- `attachment_type` : `rigid`, `pivot`, `sliding`, `flexible`, `none`, selon ce qui est effectivement supporté.

Un mode annonce `hands_required: 0|1|2` **et** une liste de contacts. Les contacts d'avant-bras ou d'épaule ne se comptent pas comme des mains additionnelles. Un objet porté par une bandoulière peut n'exiger aucune main.

### 4. Directions et repères : `functional_axes[]`

Chaque vecteur doit avoir une **origine et un sens physique identifiables visuellement** : `opening.normal_out`, `muzzle.axis_out`, `blade.edge_out`, `shield.front_normal`, `hammer.impact_normal`. Éviter `forward` ou `up` sans repère.

Référentiels autorisés : `object_local` (pièce), `world_gravity` (haut = opposé à la gravité réelle), `actor_local` (avant du personnage), `joint_local` (paume/bras), `target_vector` (direction vers une cible déclarée), `motion_path` (déplacement du clip). **Aucun rôle sémantique ne dépend du cadrage de la caméra ni du plus grand axe du maillage.**

Une **surface** (face de bouclier), un **axe** (canon) et une **trajectoire** (hache qui frappe) ne sont pas interchangeables.

### 5. Contraintes : `constraints[]`

Chaque contrainte porte `kind`, `phase_scope`, `part_ids`, `reference_frame`, `source` (`vision`, `brief`, `game_state`, `gameplay_rule`, `rig`, `mixamo`), `required`, `tolerance` (si justifiée) et `violation_effect`.

| `kind` | Exemple et garde-fou |
|---|---|
| `keep_upright` | Normale sortante de l'ouverture d'un pot orientée vers `world_gravity.up` pendant le transport rempli |
| `keep_level` | Surface de plateau, bassin ou verre maintenue sensiblement horizontale |
| `point_at` | Axe du canon, pointe de lance ou bec verseur dirigé vers une cible explicitement fournie |
| `face_toward` | Face protectrice du bouclier opposée à la menace |
| `align_with_motion` | Surface ou axe aligné avec la direction d'impact/creusement du geste |
| `follow_path` | Partie active suit une trajectoire de balayage définie par le clip et l'intention |
| `controlled_tilt` | Inclinaison intentionnelle, avec direction/cible; **désactive ou remplace** `keep_upright` pendant `pour` |
| `avoid_collision` | Tranchant/flamme ne traverse pas le torse, manche ne pénètre pas les articulations |
| `maintain_clearance` | Laisser une marge entre zone dangereuse et corps/objet protégé |
| `maintain_contact` | Paume(s), sangle, appui d'épaule restent réellement sur les régions déclarées |
| `respect_joint_limits` | Deuxième bras et poignets restent dans des poses atteignables |
| `maintain_attachment` | Sangle/bandoulière reste attachée sans main rigide fictive |
| `allow_relative_motion` | Corde, charnière, mécanisme ou contenu bouge relativement au corps principal |
| `release_at_event` | Relâcher une flèche, un projectile ou un objet au bon instant |
| `preserve_contents` | Un contenu non scellé reste contenu; si la pose viole cette condition, refuser ou déclencher la mécanique de déversement |

Les tolérances de renversement, de contact et de joint **ne se lisent pas sur un PNG**. Elles sont apportées par la physique du jeu, la taille des paumes, le type de contenu ou des paramètres explicitement approuvés. `unknown` bloque une validation qui en dépend; il ne déclenche aucune valeur universelle cachée.

## Vingt-six cas qui doivent fonctionner sans règles par nom d'objet

Chaque ligne est un **scénario à caractériser**, pas une annotation prédéfinie. Les mains, régions et contraintes réelles restent à confirmer sur les sources et le rig.

| Objet et mode | Régions/contact à détecter | Contrainte ou comportement important |
|---|---|---|
| 1. Pot d'eau ouvert, porté | Anses/corps soutenu, ouverture, contenu | `keep_upright` + `preserve_contents`; ouverture vers le haut gravitationnel |
| 2. Même pot, versé | Prise(s), lèvre d'écoulement, ouverture | `controlled_tilt` + `point_at` le récipient cible; transition explicite |
| 3. Pot vide, déplacé | Même géométrie, `contents: empty` | Pas de contrainte anti-déversement; autres contacts inchangés |
| 4. Seau d'eau suspendu | Anse articulée, récipient, ouverture | `hook` ou `grasp`, `allow_relative_motion` et anti-renversement |
| 5. Tasse remplie | Anse, bord, dessous éventuel | `keep_upright` pour porter; `controlled_tilt` pour boire |
| 6. Bouteille avec bouchon | Col, bouchon, ouverture | `closure_state` change la contrainte; main pouvant ouvrir |
| 7. Théière | Anse, bec, couvercle | `controlled_tilt` au bec et `preserve_contents` selon phase |
| 8. Torche allumée | Manche, flamme | `keep_upright` possible selon type de flamme, `maintain_clearance` du corps |
| 9. Lanterne suspendue | Anse, corps, flamme interne | `hook`, pivot relatif, éviter collision; ne pas exiger grip sur la cage |
| 10. Fusil épaulé | Poignée, garde-main, crosse, bouche, mire | Deux mains possibles + `brace` épaule + `point_at` cible |
| 11. Pistolet tenu | Poignée, détente, bouche | Une ou deux mains selon mode/pose; `point_at` axe du canon |
| 12. Arc en transport / tir | Poignée, corde, encoche, avant de l'arc | Transport éventuellement une main; tir avec main de corde et dynamique `moving_part` |
| 13. Arbalète | Poignée, crosse, rail, corde, détente | `aiming_reference`, support, état tendu/chargé |
| 14. Hache en transport / frappe | Deux prises éventuelles, manche, tranchant, tête | `maintain_contact` 1/2 mains selon image; `align_with_motion` tranchant |
| 15. Épée, taille / estoc | Garde, poignée, tranchant, pointe | Geste de taille et estoc ont des `active_surface`/`active_tip` différents |
| 16. Dague | Poignée, pointe, tranchant | Orientation de pointe et prise réellement visible; risque de collision avec le bras |
| 17. Lance | Hampe, pointe | Prises possiblement espacées; `point_at` ou `follow_path` selon estoc |
| 18. Marteau | Manche, face de frappe | `impact_normal` vers cible, pas la pointe la plus éloignée du GLB |
| 19. Bouclier à sangle | Poignée intérieure, sangle, avant du bouclier | `strap` avant-bras + `face_toward` menace; pas nécessairement deux paumes |
| 20. Pelle | Manche, prise secondaire, lame/plateau | `follow_path` creuser/soulever; la terre transportée crée une charge et un mode |
| 21. Pioche | Manche, pointe(s) de travail | `align_with_motion` vers matériau; danger de retour vers le corps |
| 22. Canne à pêche | Poignée, moulinet, ligne, pointe | `flexible_part` et tension; incompatible avec un rigide unique si simulation attendue |
| 23. Corde/grappin | Brin saisi, crochet, segments libres | `flexible`; pas de rigide global ni point de contact inventé |
| 24. Échelle portée | Montants, échelons, centres de prise | `support`/deux contacts éventuels; dégagement du sol et du corps |
| 25. Coffre à couvercle | Poignées, couvercle, charnière | Masse supportée, `allow_relative_motion`; ouvrir exige des contacts différents |
| 26. Étendard | Hampe, tissu flexible | Hampe rigide + tissu articulé/souple; orientation de la bannière distincte des mains |

**Test adversarial central :** appliquer le **même objet 3D** à des états/modalités différents. Si le moteur conserve une seule orientation « typique du pot » ou une seule prise « typique de la hache », le contrat n'est pas suffisamment générique.

## Exemple de contrat : le pot, sans inventer ses propriétés cachées

Exemple **schématique**, uniquement pour illustrer le vocabulaire. Les `part_id` doivent ensuite être **délimités par vision**, puis localisés sur le vrai GLB. Le gameplay confirme que ce pot précis est ouvert et contient du liquide.

```json
{
  "schema": "held_object_interaction_v2_proposal",
  "object_id": "pot_01",
  "source_provenance": ["object_image_sha256", "character_image_sha256", "brief_sha256"],
  "object_state": {
    "contents": {"value": "liquid", "source": "game_state"},
    "fill_state": {"value": "partial", "source": "game_state"},
    "closure_state": {"value": "open", "source": "game_state"}
  },
  "parts": [
    {"id": "pot_handle", "functional_role": "grasp_region", "region": "vision_polygon_required"},
    {"id": "pot_opening", "functional_role": "opening", "region": "vision_polygon_required",
     "functional_axis": "normal_out"},
    {"id": "pot_lip", "functional_role": "outlet", "region": "vision_polygon_required"}
  ],
  "modes": [
    {
      "id": "carry_filled",
      "hands_required": "determined_from_character",
      "contacts": [{"effector": "determined_from_rig", "contact_kind": "grasp",
                    "part_id": "pot_handle"}],
      "constraints": [
        {"kind": "keep_upright", "part_id": "pot_opening",
         "axis": "normal_out", "reference_frame": "world_gravity.up",
         "phase_scope": "carry", "required": true,
         "tolerance": "gameplay_rule_required", "violation_effect": "spill_or_reject"},
        {"kind": "preserve_contents", "phase_scope": "carry", "required": true}
      ]
    },
    {
      "id": "pour",
      "contacts": "vision_and_rig_confirmed_for_this_mode",
      "constraints": [
        {"kind": "controlled_tilt", "part_id": "pot_lip",
         "reference_frame": "target_vector", "required": true},
        {"kind": "point_at", "part_id": "pot_lip",
         "reference_frame": "target_vector", "required": true}
      ],
      "replaces_in_this_phase": ["keep_upright"],
      "events": ["pour_start", "pour_stop"]
    }
  ],
  "mixamo_pose_status": "pending_real_joint_validation",
  "visual_qa_status": "pending"
}
```

Ce n'est **pas encore un schéma JSON exécutable** : les chaînes `vision_polygon_required` et `determined_from_rig` sont des **garde-fous de conception**, pas des valeurs que le runtime doit accepter. La future implémentation devra choisir un vrai schéma versionné, des types contraints, des références valides et des champs `unknown` rejetés lorsqu'ils sont bloquants. Ne pas modifier en douce l'ancien contrat v1 pour lui faire prétendre supporter toutes ces contraintes.

## Projection déterministe : des régions reconnues aux véritables repères 3D

**Principe :** faire observer au modèle des images du **vrai GLB**, déjà placées dans un référentiel entièrement connu. Le modèle dit **ce que représente chaque partie et l'entoure**; notre renderer sait **où se trouve chaque pixel sur la vraie surface 3D**. Aucune classification « manche/tête/avant » par géométrie n'est nécessaire.

### Entrées de la reconnaissance spatiale

Pour une instance d'objet, fixer et enregistrer :

- Le GLB exact (empreinte du fichier), les transforms de ses nœuds, et sa matrice de placement `T_object_to_world`.
- Les vues réelles (face, arrière, côté, trois-quarts, dessus si nécessaire), leurs matrices caméra `view`/`projection`, dimensions, cadrage et **depth buffer** ou les informations de raycasting sur les triangles.
- Une image des vues non annotées, plus une **grille de coordonnées/pixels** de repérage; le crop éventuel garde sa transformation explicite vers l'image entière.
- Les noms et fonctions issus de la vision du concept original, son brief et l'état déclaré. Les annotations de vue GLB doivent réutiliser les **mêmes IDs**, mais la vision doit pouvoir signaler qu'une partie du concept ne se retrouve pas dans le mesh.

### Ce que la vision retourne

Pour chaque `part_id` visible dans une vue, le modèle renvoie une **région délimitée** (`bbox`, `polygon` ou `mask`), les points stratégiques **s'ils sont discernables**, la fonction, l'explication du sens physique et la visibilité. Il ne retourne **pas** une rotation Euler arbitraire ni une désignation d'axe `X/Y/Z` à deviner.

Trois formes d'annotation sont différentes et complémentaires :

| Forme sémantique | Exemples | Géométrie récupérée |
|---|---|---|
| **Région de surface** (`surface_region`) | Deux prises distinctes d'une hache; poignée d'une tasse; appui de crosse | Ensemble de triangles visibles et zone de contact admissible, pas un unique point magique |
| **Point ou zone stratégique** (`contact_anchor`, `effect_origin`, `tip`) | Centre d'une prise, bouche de fusil, pointe de lance, bec verseur | Point sur la vraie surface, normale locale et voisinage de contact |
| **Direction / plan orienté** (`oriented_axis`, `oriented_plane`) | Canon vers sa bouche, tranchant vers sa face coupante, normale sortante de l'ouverture du pot | Origine et extrémité signées, ou plan de surface avec sa normale **dont le côté est identifié par vision** |

**Avoir une région ne signifie pas connaître automatiquement la bonne prise.** Pour la main, on a besoin d'une zone saisissable **et** d'un repère de contact (`contact_frame`) compatible avec la paume : centre local, normale d'approche, tangente éventuellement orientée le long d'un manche, dimensions/largeur, état `needs_review` si l'accès n'est pas visible.

### Récupération 3D, sans devinette sémantique

1. Vérifier la cohérence de la région annotée : pixels dans l'image, intersection effective avec le rendu de l'objet, non exclusivement fond/vide, preuve explicite de la fonction. **Ne jamais déplacer la boîte pour lui donner l'air valide.**
2. Dans chaque vue, faire correspondre les pixels annotés aux **triangles réellement visibles** : par depth buffer + déprojection avec les matrices connues, ou par rayons caméra et intersection avec le mesh. En cas de transparence, d'occlusion ou de plusieurs surfaces possibles, utiliser une autre vue ou refuser le point.
3. Transformer le résultat dans les coordonnées de l'objet via l'inverse de `T_object_to_world` (et les transforms des nœuds GLB), et le conserver comme référence stable à la **primitive/face + coordonnées barycentriques**, avec surface/normal/tangente. Une approximation au sommet voisin n'est pas la seule stratégie et n'est pas une preuve suffisante si elle tombe loin de la région.
4. Reconstruire les **axes signés** à partir de deux landmarks visuellement identifiés, ou les **plans** à partir d'une région identifiée et de sa normale. Un produit vectoriel / une normale du mesh peut calculer la géométrie, mais **la vision indique quel signe correspond au dessus, à l'extérieur, au tranchant ou à la sortie**.
5. Faire contrôler le **même rôle** dans plusieurs angles : projections 3D compatibles, ID stable, direction signée cohérente; les éléments invisibles restent `unresolved`, pas interpolés vers l'extrémité géométrique la plus proche.
6. Stocker pour chaque ancre : `part_id`, `role`, `source_view`, `annotated_region`, `mesh_node`, `mesh_primitive`, `triangle_id`, `barycentric_coordinates`, `local_position`, `local_surface_normal`, `local_tangent` (si utile), `signed_axis`/`plane` (si démontré), `evidence`, `projection_error`, `status`.

En notation géométrique : pixel + **profondeur connue** → point monde par déprojection caméra → point local par `inverse(T_object_to_world)`. La matrice caméra et la profondeur sont des **mesures du renderer**, pas des prédictions du modèle.

### À quoi ces repères servent ensuite

| Objet | Régions identifiées par vision | Repères 3D utilisables |
|---|---|---|
| **Pot** | Anse/corps, ouverture, lèvre | `grasp_region` + plan de l'ouverture; **normale sortante** comparée au haut gravitationnel pour `keep_upright`, puis lèvre orientée vers la cible pendant `pour` |
| **Fusil** | Poignée, garde-main, crosse, bouche, mire | Contacts main/main/épaule + axe signé **crosse → bouche** pour `point_at`; ne pas confondre avec l'axe principal d'un maillage |
| **Hache** | Manche inférieur/supérieur, tête, face tranchante | Deux zones de contact, repère longitudinal du manche, direction vers **le vrai tranchant**, trajectoire déterminée par le geste |
| **Épée** | Poignée, tranchant, pointe, garde | Repère de paume + **axe de pointe** (estoc) distinct de la **normale du tranchant** (taille) |
| **Bouclier** | Poignée arrière, sangle, face protectrice | Région d'attache à l'avant-bras + **normale signée de la face avant** vers la menace |
| **Torche / lanterne** | Zone de prise ou suspension, foyer/flamme | Repère d'accroche + direction de la flamme et marge d'éloignement du corps; la suspension peut pivoter relativement à la main |

Ce qui dépend de **l'objet** (points, régions, normales et axes) devient réutilisable avec différents personnages. Ce qui dépend du **personnage/clip** (paume, reachabilité, IK, trajectoire) se résout ensuite, sans refaire la classification sémantique pour chaque animation. Ce qui dépend du **monde/état** (gravité, cible, liquide, remplissage) s'évalue à chaque mode et pose.

**Interdictions :** ne pas utiliser une PCA pour décider de la tête ou du tranchant; ne pas remplacer une normale signée inconnue par le signe arbitraire du mesh; ne pas supposer qu'un rectangle 2D à lui seul révèle une surface cachée; ne pas déduire que le pot est rempli d'après sa forme; ne pas confondre un repère de prise avec une pose de main déjà validée.

## Questions exactes à poser au modèle vision

La requête doit demander, dans cet ordre :

1. **Identité et preuves** — Que représente l'objet visuellement? Qu'en dit le brief? Toute contradiction? Qu'est-ce qui est impossible à savoir depuis les images (contenu, étanchéité, température, chargement, poids)?
2. **Inventaire des parties** — Pour chaque région ayant une fonction (prise, support, attache, action, ouverture, sortie, face de protection, zone dangereuse ou élément mobile), fournir **ID, rôle, fonction, boîte/polygone ou masque, preuve visuelle et confiance**. Ne pas inférer la fonction de l'extrémité la plus longue.
3. **Axes avec sens physique** — Identifier les normales/axes utiles : direction de sortie, tranchant, dessus d'ouverture, avant du bouclier, etc. Préciser origine, sens et référentiel. Aucun `up` ou `forward` ambigu.
4. **Contacts sur le personnage** — Quelles mains ou autres zones du corps sont réellement montrées en contact? Le caractère est-il tenu, soutenu, suspendu ou calé? Délimiter les régions sur la source. Ne pas transformer une proximité en prise.
5. **Modalités** — Quels modes sont nécessaires (porter, viser, frapper, boire, verser, recharger, ouvrir, relâcher...) et que change chacun dans les contacts, états et contraintes? Séparer observation, hypothèse et règle confirmée.
6. **Conséquences physiques** — L'objet doit-il rester vertical, horizontal, orienté vers une cible, hors du corps, ou peut-il être renversé? **Sur quelle preuve** (image/brief/état de jeu) repose chaque contrainte? Les tolérances non observables restent inconnues.
7. **Compatibilité Mixamo provisoire** — Quel rôle de clip réel paraît candidat? Cette réponse **n'est jamais** une preuve de prise ni de compatibilité du geste.
8. **Incertitudes bloquantes** — Quelles régions, prises, directions et états demandent une revue? Ne pas émettre `confirmed` par simple confiance élevée.

Un second modèle de vision peut vérifier **des annotations superposées** sur les images (objet et personnage), mais pas seulement réécrire les points dans un JSON. Le solveur reçoit uniquement les régions acceptées. L'état du jeu et les règles physiques restent des sources distinctes de la vision.

## Contrats de vérité et QA

Déclarer séparément :
- `semantics_confirmed` : rôles et régions visuellement et sémantiquement validés;
- `state_and_rules_confirmed` : contenu, étanchéité et autres contraintes de gameplay connus;
- `glb_regions_confirmed` : mêmes rôles localisés sur le vrai maillage, sans attribution heuristique;
- `pose_contacts_confirmed` : contacts réels avec les articulations à des instants déterministes;
- `pose_constraints_confirmed` : dessus du pot vers la gravité, canon vers la cible, tranchant orienté, etc.;
- `independent_visual_qa_confirmed` : captures multiangles évaluées par vision, par mode et pose.

**Aucun des six statuts ne découle automatiquement d'un autre.** Le verdict global n'est positif que si chaque contrainte requise par le mode est satisfaite. Un pot incliné en transport **échoue** même si ses deux mains sont parfaitement placées. Un fusil visé vers l'arrière **échoue** même si la main touche la poignée. Une hache dont la main secondaire flotte **échoue** même si son tranchant pointe dans la bonne direction.

## Adoption progressive et anti-régression

1. Faire évoluer le vocabulaire/contrat **sans détruire les reçus v1 ni les sorties existantes**; la migration doit être explicite.
2. Implémenter d'abord la caractérisation **sur un pot rempli et une hache** : ces deux pilotes forcent des contraintes de nature différente (gravité/état vs orientation d'action/deux mains).
3. Vérifier ensuite au moins le fusil (axe de visée et appuis multiples), l'arc (contact et pièce mobile), le bouclier (avant-bras/sangle) et la lanterne (suspension/pivot) avant de prétendre à la généricité.
4. Tester les **transitions d'état et de mode** (pot plein → vidé; porter → verser; porter l'arc → tirer; garde → impact) aux mêmes instants déterministes.
5. Ne pas appeler le système « générique » tant que ces contre-exemples n'ont pas des rendus et verdicts traçables. Les 26 lignes constituent une **matrice de conception**, pas 26 réussites déjà démontrées.
