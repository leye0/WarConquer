# Plan de référence — objets tenus : vision, articulations et QA par poses

**Statut : décision d'architecture et protocole de validation, pas une preuve que la hache fonctionne.**  
**Date : 2026-10-28**  
**Portée :** tout objet avec action tenu par un personnage (hache, arc, bouclier, fusil, outil, etc.), toutes les unités et tous les clips Mixamo.  
**Complément :** [contrat technique existant](../docs/prop-interaction-contract.md).
**Vocabulaire contractuel obligatoire :** [affordances, états, contacts, contraintes et 26 scénarios](held-object-affordance-contract.md). Les rôles/fonctions de l'objet et les contraintes dépendant de son état sont deux domaines distincts; aucune règle par nom d'arme.

## Résultat attendu

Un personnage tient réellement l'objet au bon endroit, avec la ou les mains attendues, dans les poses de repos, de déplacement et d'action. La partie fonctionnelle de l'objet (tranchant, bouche du canon, corde de l'arc, surface d'impact...) est correctement orientée selon l'intention de l'action. Un verdict « prêt » doit être démontré sur des rendus **réels** et des mesures des articulations animées, pas inféré de tests unitaires qui passent.

## Feuille de route détaillée — cases à cocher et preuves

**Référence d'avancement : branche `feat/semantic-prop-contact-contract`, pilote `marches_hache`, état au 2026-10-28.** `[x]` signifie qu'un livrable précis existe et est identifiable dans le dépôt, **pas** que l'étape suivante a été validée. `[ ]` signifie non démontré, incomplet ou rejeté. Toute case portant sur la qualité de prise reste ouverte jusqu'à vérification sur le rendu réel. La hache est actuellement **`VISUAL_NO_GO`**, malgré les distances de paumes numériquement acceptées par le prototype.

**Preuves existantes :** `assets/experiments/props/marches_hache/trellis-v1/interaction-contract.json` (sens et modes de la hache), `scripts/rig-contact-landmarks.js` (repères anatomiques), `scripts/character-lab-client.js` (prototype de fitting/IK), `scripts/capture-prop-contact.mjs` (captures/mesures), `scripts/verify-prop-visual-qa.py` et `scripts/run-prop-visual-qa.py` (verdict indépendant), `assets/experiments/props/marches_hache/trellis-v1/grip-plan.json` (`visual_qa.status: rejected`). Ces preuves ne démontrent **ni** un repère de surface 3D complet **ni** une prise anatomiquement correcte.

### A — Verrouiller le contrat avant de déplacer l'objet

- [x] A1. Conserver le concept objet, le concept personnage, le brief, les empreintes d'entrées et le GLB du pilote.
- [x] A2. Faire confirmer sur les sources la hache, le vrai tranchant, les deux régions de manche, la main droite principale, la gauche secondaire et les modes `carry_mode` / `use_mode_chop`.
- [ ] A3. Généraliser un schéma **exécutable et versionné** du triplet `object × character × Mixamo`, sans prétendre que le contrat v2 conceptuel est déjà déployé.
- [ ] A4. Pour chaque mode, valider `hands_required`, côté principal/secondaire, nature de contact (`grasp`, `support`, `brace`, `strap`, `hook`, etc.), `part_id`, événement de prise/relâchement et rôle de clip candidat.
- [ ] A5. Séparer les faits visibles, les choix de gameplay, l'état réel (`contents`, fermeture, chaleur, charge), les dimensions de l'objet et les inconnues bloquantes; ne jamais attribuer un contenu à partir de la silhouette.
- [ ] A6. Définir les axes fonctionnels **signés** par leur sens physique (tranchant, ouverture, sortie, face protectrice), les contraintes actives **par mode et par phase**, et leurs sources.
- [ ] A7. Rejeter le contrat incomplet au lieu de choisir implicitement un nombre de mains, un axe ou un point de prise.

**Sortie de phase :** contrat de mode traçable, sans rôle inventé, dont chaque exigence possède une source et un statut.

### B — Passer de la région vision à une véritable surface 3D

- [x] B1. Faire produire des images fixes du **GLB réellement texturé et chargé dans le renderer**, avec caméras connues; conserver les images offertes à la vision.
- [ ] B2. Exiger pour chaque `part_id` une **boîte/polygone/masque étiqueté**, dans le repère explicite de l'image/crop; tester sa présence sur des pixels visibles de l'objet (pas sur du vide).
- [ ] B3. Faire vérifier les surimpressions des régions et les directions par une seconde passe vision; demander des vues supplémentaires si prise, dessous ou tranchant sont occultés.
- [ ] B4. Croiser **les mêmes IDs** sur plusieurs vues du GLB; documenter contradictions, ambiguïtés de profondeur et surfaces manquantes.
- [ ] B5. Déprojeter les pixels de région avec **matrices de caméra + profondeur ou raycast réel** pour obtenir les triangles réellement rencontrés. Interdiction de substituer le sommet le plus proche comme preuve de contact.
- [ ] B6. Enregistrer une **zone de surface 3D** (`mesh_node`, primitive, triangles, barycentriques, limites de la zone), sa normale physique, ses tangentes utiles, son épaisseur/largeur accessible et son incertitude.
- [ ] B7. Construire le `contact_frame` 6D local et les axes/plans d'action **uniquement depuis les régions identifiées**; la vision lève les ambiguïtés de signe et de fonction, la géométrie mesure.
- [ ] B8. Reprojeter la zone et le repère 3D sur toutes les vues; valider en vision que **la prise touche toujours la bonne partie**, sans saut d'ID ou de face.

**Sortie de phase :** *surface saisissable* et repères 3D prouvés, pas seulement `grip_point: [x,y]` ni un sommet isolé.

### C — Calibrer le personnage réel et les poses Mixamo

- [x] C1. Repérer sur le vrai rig les deux chaînes épaule → coude → poignet et leurs positions animées.
- [x] C2. Calculer un prototype de `palmFrame` avec centre de paume, direction des doigts, axe transversal et normale à partir des articulations.
- [ ] C3. Vérifier sur rendus les signes et repères anatomiques gauche/droite (paume versus dos de main, pouce, doigts, intérieur du poignet), y compris les éventuels axes locaux inversés.
- [ ] C4. Repérer et qualifier les **véritables articulations des doigts et des pouces**; distinguer rig sans doigts, rig partiellement articulé et rig complet.
- [ ] C5. Extraire les longueurs, orientations de repos, limites articulaires, volumes de main/avant-bras et échelle effective **du rig présent**; les seuils dépendent des dimensions mesurées.
- [ ] C6. Évaluer les frames Mixamo exactes, après transformations hiérarchiques, pour chaque mode; conserver les poses sources pour mesurer toute modification de l'IK.
- [ ] C7. Vérifier les zones de peau et les faces de paume qui entreront réellement en contact, au lieu de confondre l'origine de l'os de main avec une prise crédible.

**Sortie de phase :** repères de paumes orientés et articulations fiables dans **chaque** pose, sans convention arbitraire issue de la caméra.

### D — Remplacer le prototype « deux points » par une préhension articulée

- [x] D1. Disposer d'une première résolution à deux cibles de paumes et d'une IK de bras **de prototype**, utile au diagnostic mais non suffisante pour `GO`.
- [ ] D2. Définir le contact comme une contrainte de **surface + orientation** : position admissible dans la région, normale d'approche de paume, tangente/axe de prise, envergure de la main, type de contact et éventuel glissement.
- [ ] D3. Résoudre la transformation rigide de l'objet **et** l'orientation de la main principale avec ce repère : le manche doit traverser les doigts, non seulement passer près du poignet.
- [ ] D4. Résoudre **simultanément** la prise secondaire, les deux chaînes de bras et les **poignets**, avec coudes anatomiquement plausibles; une main ne peut pas être validée en isolant l'autre.
- [ ] D5. Respecter l'orientation des paumes et du pouce opposable autour de la vraie section 3D; quand le rig le permet, adapter les phalanges et mesurer leurs contacts/collisions.
- [ ] D6. Conserver les contraintes du clip et les limites du rig, éviter torsions extrêmes, croisements de bras, traversées de torse et pénétrations de la tête ou du tranchant.
- [ ] D7. Gérer aussi les **autres types de contact** sans imposer le solveur de serrage à la sangle, à l'épaule, au plateau soutenu ou à l'objet suspendu.
- [ ] D8. Définir une fonction de coût et des contraintes dures **explicites**, avec résidus séparés par paume, poignet, doigts, objet, collision et rôle fonctionnel. Les poids, seuils et tolérances doivent être justifiés par l'échelle/le mode.
- [ ] D9. Renvoyer `unreachable` / `incompatible_mixamo` / `insufficient_surface_evidence` lorsque les contraintes sont insolubles; ne pas inventer une orientation, déplacer une région sémantique ou permuter les mains pour fabriquer un succès.

**Sortie de phase :** un objet **réellement saisi** en 6 degrés de liberté et des poignets/doigts cohérents, ou un refus explicable.

### E — Respecter la fonction de l'objet à travers les phases animées

- [x] E1. Échantillonner des frames fixes Mixamo déterministes du transport, de la marche, de la course et de la frappe, dont plusieurs instants de l'action.
- [ ] E2. Appliquer à chaque frame les **contacts actifs de la phase** et leurs fenêtres de relâchement, au lieu d'une seule pose de main pour toute l'animation.
- [ ] E3. Contrôler l'axe/surface fonctionnel(le) signés par rapport à l'intention : tranchant pendant la frappe, bouche vers la cible, face du bouclier vers la menace, etc.
- [ ] E4. Appliquer les contraintes d'état : ouverture du pot vers la gravité en transport **rempli**, inclinaison contrôlée pendant `pour`, suspension/pivot, pièces mobiles selon les capacités réelles du moteur.
- [ ] E5. Mesurer les transitions entre échantillons (contacts, rotations, collisions, vitesse, relâchement) et ajouter des frames **fixes** aux zones suspectes, sans imposer de vidéo.
- [ ] E6. Déclarer incompatible le clip dont le geste réel contredit les prises ou la direction fonctionnelle, puis sélectionner explicitement un autre clip si disponible.

**Sortie de phase :** une interaction correcte **tout au long des modes**, pas une capture avantageuse.

### F — Tests numériques et tests adversariaux avant vision

- [x] F1. Produire déjà les distances numériques de paume aux prises et une première mesure de dégagement du torse; conserver ces métriques comme **diagnostic**, sans les appeler « prise validée ».
- [ ] F2. Mesurer la distance **signée à la surface de préhension**, la position à l'intérieur de la zone admise, l'orientation normale et la rotation de la paume par rapport au `contact_frame`.
- [ ] F3. Mesurer l'entourage du manche par les doigts et le pouce, le nombre et la qualité des contacts utilisables, et toute pénétration excessive dans l'objet.
- [ ] F4. Vérifier limites des épaules/coudes/poignets, collisions par membres/objet, dégagement des zones dangereuses et exigences d'orientation de l'action.
- [ ] F5. Définir des seuils **à l'échelle de l'objet et du rig** (largeur du manche, paume, espacement, phase, marge de pénétration), documentés et testés, plutôt que considérer `0,045 m` comme preuve universelle.
- [ ] F6. Ajouter des tests qui **doivent échouer** : paume tournée de 180° malgré centre correct, doigts ouverts, mains interverties, contact au mauvais bout du manche, grip dans le vide, faux dessus du pot, arme visant derrière, épaule traversée, clip inaccessible.
- [ ] F7. Tester les entrées incomplètes et les vues contradictoires; la réponse attendue est `needs_review`, jamais une réussite obtenue par repli géométrique.

**Sortie de phase :** les erreurs observées par les modèles vision deviennent des **régressions numériques vérifiables**, sans remplacer l'inspection visuelle.

### G — Boucle de rendus et modèles vision indépendants

- [x] G1. Capturer de vraies images fixes du rendu Babylon/Character Lab à des temps Mixamo reproductibles, avec cadrage de contrôle et gros plans.
- [x] G2. Interroger deux modèles vision indépendants via OpenRouter pour un verdict `GO/NO-GO`; conserver leurs refus. **Dernier constat : deux `NO-GO`, donc pilote rejeté.**
- [ ] G3. Sauvegarder et afficher côte à côte **exactement les PNG soumis au modèle**, leurs IDs de frame/vue, les boîtes et labels retournés, et les captures annotées reprojetées sur le GLB.
- [ ] G4. Exiger l'inspection explicite de **chaque** prise attendue : vraie région du manche, contact paume et doigts, orientation du poignet, main secondaire, direction de l'effet, collisions; `occluded`/`unresolved` ne signifie pas `GO`.
- [ ] G5. Faire produire des vues face, profil, trois-quarts et gros plans **aux instants problématiques**, en conservant une version **sans annotations** pour le jugement indépendant.
- [ ] G6. Après chaque correction, recapturer **les mêmes frames et caméras** et comparer les preuves avant/après; un score numérique qui monte alors que le verdict visuel reste négatif n'est pas un progrès accepté.
- [ ] G7. Séparer et archiver `semantic_status`, `glb_surface_status`, `anatomy_status`, `numeric_pose_status`, `independent_vision_status`, `overall_status` avec raisons par mode et par frame. `overall_status=GO` exige **tous** les critères requis.
- [ ] G8. Conserver les appels OpenRouter et leurs coûts (modèle, prompt, version, empreinte d'image, réponse brute, incertitude); autoriser des appels ciblés supplémentaires et le cache, sans plafond historique arbitraire d'une requête.
- [ ] G9. Avant déclaration ou fusion, ouvrir **personnellement les PNG produits par WebSuite/CI**, confirmer le comportement de la vraie scène et l'accord entre métriques et vision.

**Sortie de phase :** dossier de preuve reproductible, lisible par le développeur **et** par l'utilisateur, avec verdict indépendant et causes des échecs.

### H — Démonstration de généricité, après la hache

- [ ] H1. Obtenir **GO numérique + vision pour toutes les poses critiques** de `marches_hache` en transport, déplacement et frappe, sans main flottante.
- [ ] H2. Faire un second pilote : **pot rempli ouvert**, puis le *même* GLB vide, rempli scellé et en mode `pour`; vérifier états, gravité et transitions.
- [ ] H3. Tester le **fusil** (deux mains + épaule + bouche orientée), l'**arc** (corde/contact mobile), le **bouclier** (sangle avant-bras), la **lanterne** (suspension/pivot).
- [ ] H4. Étendre progressivement la matrice des **26 scénarios** du [contrat d'affordances](held-object-affordance-contract.md) avec preuves et contre-exemples, sans écrire de branche spéciale « si hache » / « si pot » dans le solveur.
- [ ] H5. Publier/fusionner la fonctionnalité uniquement lorsque les critères des modes annoncés sont réellement démontrés; ne jamais présenter l'ensemble des 26 scénarios comme implémenté avant leurs vérifications.

**Ordre de priorité immédiat :** **B5–B8** (surface réelle) → **C3–C7** (paume/poignet/doigts) → **D2–D9** (préhension 6D couplée) → **F2–F7** (régressions) → **G3–G9** (preuve visuelle) → **H1** (hache). Les fondations déjà cochées sont réutilisées; on n'accumule pas de nouveaux essais de rotation du manche autour de deux points.

## Principes non négociables

1. **La vision attribue les significations.** Le modèle de vision, aidé du concept original, du brief et du personnage, identifie et **délimite visuellement** les régions de prise et les parties fonctionnelles. Un couple `[x, y]` émis dans un JSON **sans délimitation ni contrôle de localisation** ne suffit pas.
2. **La géométrie ne devine aucune fonction.** Jamais de « l'extrémité la plus longue est la lame », « l'axe principal désigne le devant », « la plus grande surface est la poignée » ou de solution équivalente par PCA, boîte englobante, centroïde ou extrémité du maillage. La géométrie peut projeter, ajuster et mesurer **uniquement des rôles déjà nommés par la vision**.
3. **Trois sources, chacune à sa place : objet × personnage × Mixamo.** L'objet donne ses régions et directions fonctionnelles; le personnage donne ses articulations, paumes et dimensions; le clip donne ses **poses animées réelles**, pas seulement un nom prometteur.
4. **Les modes sont explicites dès le début.** Transport, garde, action, rechargement, etc. ont chacun leurs prises, main principale, éventuelle main secondaire, direction fonctionnelle et rôle Mixamo. Le nombre de mains peut varier d'un mode à l'autre.
5. **Deux mains signifient deux contacts démontrés.** Une orientation visuellement séduisante de l'objet ne compense pas une seconde main distante. Ne jamais annoncer `fully_ready` si un contact est manquant, si la pose du clip ne le permet pas ou si l'action fonctionnelle pointe dans la mauvaise direction.
6. **Aucun point inventé pour sauver un résultat.** Si une région ne peut être localisée, un point tombe hors de l'objet ou une pose est anatomiquement impossible, on marque la cause `needs_review` / `unresolved`. On ne déplace pas silencieusement une annotation et on n'invente pas une rotation propre à cette arme.
7. **QA par rendus fixes reproductibles.** Pour les vérifications visuelles, utiliser des captures de poses déterministes, prises sous plusieurs angles et analysées par un modèle de vision. **La vidéo n'est pas une condition de validation.** La stabilité au cours du temps se contrôle par un échantillonnage de poses.

## Stratégie : exploiter intensivement la vision OpenRouter

**Objectif : maximiser la qualité et les preuves visuelles, pas minimiser le nombre d'appels.** Les modèles vision sont suffisamment peu coûteux pour intervenir **à plusieurs reprises**, avec des missions ciblées et des résultats contrôlables. Une requête par objet ne suffit pas à établir à la fois sa fonction, sa position 3D et sa compatibilité avec un personnage animé.

| Moment du flow | Rôle concret du modèle vision | Preuve attendue |
|---|---|---|
| **Concept original + personnage** | Identifier les fonctions, les modes et les prises visibles; signaler les états non observables | Parties nommées, boîtes/polygones, mains et incertitudes |
| **Contrôle indépendant du concept** | Relire les **surimpressions réelles** et relever prise hors objet, faux tranchant, confusion des mains | Verdict par ID + localisation des désaccords |
| **GLB réel sous plusieurs angles** | Retrouver **les mêmes IDs** dans les rendus avec caméras connues; identifier dessus, arrière, côtés, sortie, tranchant, contacts | Régions par vue, axes/sens étiquetés, ambiguïtés |
| **Contrôle de projection 3D** | Vérifier visuellement les points/axes reprojetés sur **chaque rendu**, corriger seulement les régions dont la preuve est insuffisante | Surimpressions de points et directions + verdict |
| **Choix des modes et clips** | Comparer le concept et les **poses réelles Mixamo**, pas seulement leur nom | Prises/mains attendues, possibilités et incompatibilités visibles |
| **QA des captures d'animation** | Examiner systématiquement **plusieurs poses fixes par mode**, de plusieurs angles, avec et sans annotations | Verdict structuré par pose, main, face active, direction, collision |
| **Après correction** | Revoir **les mêmes poses et repères** avant/après, demander des vues supplémentaires si le problème persiste | Diff des erreurs et nouvelle preuve visuelle |
| **Régressions** | Rejouer les contrôles visuels seulement quand un contrat, GLB, rig, clip ou solveur change | Comparaison à des captures de référence conservées |

**Répartition des responsabilités :** vision = *sens, régions, plausibilité visible*; géométrie = *déprojection, surfaces, distances, IK, limites*; état du jeu = *contenu et contraintes physiques*. Un jugement vision positif **ne remplace jamais** la vérification 3D, et inversement.

**Politique d'utilisation des appels :**

- Autoriser **plusieurs appels payants distincts par objet et par étape**, chacun avec son objectif, son ensemble d'images et son schéma de sortie. Le verrou historique `maximum_paid_requests: 1` de la caractérisation v1 **n'est pas la politique cible du flow v2**.
- Demander un **deuxième regard indépendant** pour les rôles critiques (prises, dessus/ouverture, tranchant, bouche de canon) ou en cas de désaccord. Utiliser un modèle spatial différent si cela améliore la robustesse; ne pas simplement faire répéter une réponse incertaine.
- Regrouper intelligemment plusieurs captures pertinentes dans une même requête de QA lorsque le modèle peut encore identifier sans ambiguïté **vue, mode et instant**. Préférer des sous-ensembles lisibles à une mosaïque incompréhensible.
- Mettre en cache les analyses par empreinte **sources + images rendues + version du prompt/modèle + mode/pose** : aucun paiement pour reproduire une réponse identique. Sauvegarder l'original brut **avant** validation.
- Autoriser des **révisions ciblées** (nouvelle vue, nouvelle annotation, vérificateur indépendant) lorsque les validations échouent, avec budget **configurable et explicite** par étape, plafond global par objet et historique du coût. Zéro boucle infinie, mais **ne pas confondre « pas de retry aveugle » avec « un seul appel permis »**.
- Choisir des modèles rapides/économiques pour l'annotation et la QA courante; réserver les modèles plus puissants aux ambiguïtés persistantes ou aux contradictions entre vues. Ne pas sacraliser un fournisseur.
- En cas de blocage ou budget atteint : conserver les preuves et `needs_review`, pas une approximation géométrique présentée comme une réussite.

**Critère de performance :** un appel est utile s'il élimine une ambiguïté, confirme un repère ou juge une pose. Le nombre d'appels en soi n'est ni un score de qualité ni une raison de se priver d'une vérification nécessaire.

## Flow obligatoire

### 1. Caractériser et délimiter l'objet avant tout fitting

- Figer l'image originale de l'objet, l'image du personnage, le brief et leurs empreintes; conserver le reçu original du modèle, même si la réponse est refusée.
- Demander à un modèle de vision compatible avec la localisation spatiale de **tracer des boîtes ou polygones nommés** (ou des masques de segmentation, si disponibles) autour de chaque **région** : prise principale, prise secondaire éventuelle, partie active, direction/avant de l'action.
- Utiliser une image source recadrée de façon traçable, éventuellement quadrillée; conserver la transformation crop → pixels de l'image originale. Les boîtes doivent être visualisables en surimpression sur l'image, et non simplement décrites par du texte.
- Vérifier automatiquement la plausibilité **géométrique** de ces délimitations (coordonnées dans l'image; intersection avec les pixels visibles lorsque la transparence existe; taille non dégénérée; séparation de prises distinctes). Ce contrôle **ne sert jamais** à attribuer une fonction à une région.
- Vérifier **sémantiquement** les régions contre l'objet, son brief et le personnage. Une boîte sur le manche n'est pas automatiquement la bonne prise : il faut la preuve de l'identité et du mode d'emploi.
- Émettre un contrat source-versionné de rôles, régions, contacts et modalités, avec incertitudes et motifs de refus. Si l'incertitude porte sur une fonction ou une main, demander une revue visuelle ciblée et versionnée; une nouvelle analyse ciblée peut être lancée dans le budget approuvé, jamais une répétition aveugle.

**Garde-fou de régression :** dans le cas pilote de la hache, la première réponse OpenRouter plaçait une prise sur `[0.15, 0.85]` et l'extrémité de la direction du tranchant sur `[0.88, 0.28]` dans le PNG original 1600 × 1600, deux zones transparentes. **Ces points doivent être rejetés**; l'existence d'une valeur numérique et une confiance élevée ne les valident pas.

### 2. Localiser ces mêmes rôles sur le GLB réel

- Produire plusieurs rendus orthographiques **du GLB généré**, avec repères de vues et transformations connues.
- Faire localiser par vision **chaque ID du contrat**, en respectant sa région et sa direction fonctionnelle. Une prise ou une surface active absente du GLB est un échec explicite.
- Ne reprojeter sur une surface 3D qu'un rôle préalablement identifié; rejeter les ambiguïtés de profondeur, les projections trop lointaines et les directions fonctionnelles qui s'effondrent.
- La correspondance pixels → surface 3D utilise **la caméra et le depth buffer connus** (ou raycasting des triangles), puis un repère local stable : face/coordonnées barycentriques, normale, tangente, direction signée. Le modèle désigne le **rôle et la région**, le moteur calcule la **géométrie**, sans en inventer la fonction. Voir le [contrat de projection 3D](held-object-affordance-contract.md#projection-déterministe--des-régions-reconnues-aux-véritables-repères-3d).
- Une ouverture de récipient requiert son **plan et sa normale sortante**; un fusil son **axe vers la bouche**; une hache ses **contacts et le côté tranchant**. Les signes « dessus/devant/extérieur » doivent être caractérisés visuellement, jamais choisis par un axe arbitraire.
- Conserver surimpressions et coordonnées vérifiables. Aucun héritage de repères historiques définis par « extrémité géométrique » ne peut être présenté comme confirmé.

### 3. Ajuster objet, squelette et clip

- Lire et vérifier les **repères orientés** des paumes, poignets, doigts, coudes et épaules **à l'instant réel du clip Mixamo**; reconstruire le bon sens des normales de paume et des axes des doigts pour chaque côté du rig.
- Le fitting doit résoudre un **contact de surface orienté (6D)** : position dans une zone de prise autorisée, normale d'approche de la paume, tangente/axe de tenue, taille de la main et contraintes de contact associées. Une distance entre deux points ne démontre pas une prise.
- Optimiser de façon **couplée** la transformation rigide de l'objet, les deux chaînes épaule/coude, **les poignets et la posture des doigts/pouces lorsque le rig le permet**, ainsi que la direction fonctionnelle du mode. Toute résolution doit respecter limites articulaires, absence de collision dangereuse et déformations raisonnables de la pose source.
- Les contacts `support`, `brace`, `strap` ou `hook` sont résolus selon leurs contraintes propres, sans simuler une pince de doigts fictive. Les tolérances sont justifiées par la zone de surface et les dimensions du personnage.
- Ne pas modifier les données source Mixamo pour maquiller un résultat. Si la pose animée ne permet pas les contacts exigés, la rejeter avec cause explicite ou choisir un autre clip compatible. Une main tournée à 180° avec le bon centre de paume reste un **échec**.

### 4. Tester par images fixes et mesures 3D

Pour chaque mode requis, sélectionner **des instants déterministes et conservés** :
- repos/transport : plusieurs poses significatives;
- marche et course : plusieurs phases du cycle, dont les positions extrêmes des bras;
- action : départ, préparation, armement, phase médiane, impact/effet, récupération, retour au repos;
- autres modalités : instants où chaque prise doit apparaître/disparaître.

À **chaque** instant :
1. Capturer le personnage et l'objet dans le véritable renderer, au moins de face, de côté et en trois-quarts lorsque nécessaire.
2. Générer au besoin une version **annotée** (IDs, régions, paumes, articulations, direction d'action) et une version **non annotée**, pour ne pas tromper l'évaluation visuelle.
3. Mesurer en 3D, avec des tolérances définies et testées relativement à l'échelle réelle : **contact sur le patch de surface 3D**, résidus de position **et de rotation** des paumes/poignets, fermeture et pénétration des doigts si articulés, faisabilité des bras, collisions, contraintes d'état et orientation de la partie active. Une distance paume→point seule est insuffisante.
4. Soumettre les rendus à un **vérificateur vision** distinct du raisonnement de fitting. Il rend un verdict structuré par pose et par critère : contact droit/gauche, prise sur le bon élément, sens du tranchant/de l'effet, vraisemblance anatomique, intersection indésirable, confiance et preuve visible.
5. Enregistrer les images, mesures, verdicts, horodatages du clip et empreintes des sources de manière comparable d'un essai à l'autre.

L'échantillonnage temporel peut être densifié pour une transition suspecte **sans exporter de vidéo**. Les tests numériques de continuité complètent les captures visuelles : un modèle de vision ne peut pas inférer la stabilité de frames non observées.

### 5. Boucle de correction bornée, sans dérive sémantique

- **Erreur de région sémantique :** revoir la vision source (nouvelle révision explicite); ne pas corriger par la forme du GLB.
- **Erreur de projection GLB :** revoir la localisation visuelle du même rôle sur les vues GLB.
- **Erreur de pose/contact :** corriger transformation, IK ou choix explicite du clip, puis recapturer **les mêmes instants**.
- **Erreur de direction d'action :** revenir à la direction fonctionnelle caractérisée; aucun retournement ou signe « essayé au hasard ».
- Fixer un nombre d'essais, un budget par étape et un plafond global. Autoriser les **requêtes vision ciblées supplémentaires** nécessaires au diagnostic, sans répétition identique ni boucle payante aveugle. Conserver les réponses brutes, décisions et raisons d'arrêt.

## Critères d'acceptation (« Definition of Done »)

Un objet/mode est accepté uniquement lorsque :

- [ ] Les régions de prise et la partie active ont des **délimitations visuelles inspectables**, reliées aux images sources et au brief.
- [ ] Les mains attendues et leurs prises sont explicites pour **chaque modalité**, avec un rôle Mixamo réellement disponible.
- [ ] Les mêmes IDs sont localisés sur **le GLB réel**; aucune fonction n'a été déduite de la longueur, de l'axe ou d'une extrémité.
- [ ] Toutes les poses critiques ont été réellement rendues, sauvegardées et évaluées sous les angles nécessaires.
- [ ] Le vérificateur vision juge plausibles les contacts, l'anatomie et la partie active, **et** les mesures 3D satisfont des tolérances physiques définies.
- [ ] Le mode deux mains conserve **deux contacts distincts** là où ils sont exigés; une main absente est un échec bloquant.
- [ ] Les prises reposent sur **des zones de vrais triangles GLB** avec normales/tangentes reprojetées et vérifiées, pas sur des sommets approximatifs.
- [ ] Les paumes et **poignets sont correctement orientés** et, si les doigts sont animables, la fermeture/les contacts sont crédibles sur le vrai maillage.
- [ ] Un test adversarial rejette une main tournée de 180° à position correcte et un clip qui ne permet pas les contacts déclarés.
- [ ] Les exigences d'état et de contact sont évaluées pour **chaque mode et phase**, et pas présumées correctes à partir d'une seule pose.
- [ ] Les retours de tests et les rendus ont été inspectés (pas uniquement le statut vert d'une Action).
- [ ] Les cas ambigus/incompatibles restent explicitement rejetés, avec preuve et cause; aucune réussite n'est annoncée sans rendu convaincant.

## Ordre de travail et discipline

1. Terminer **une seule unité pilote et ses modes** de bout en bout avec images et mesures concluantes, avant d'élargir le pipeline.
2. Ne pas ajouter une nouvelle abstraction, règle ou service sans démontrer quelle défaillance observée il corrige.
3. Réutiliser la mécanique existante de captures Character Lab/WebSuite et les contrats existants; limiter le travail périphérique.
4. Mesurer l'avancement par **poses réellement validées**, pas par nombre de fichiers, commits, tests verts, appels OpenRouter ou étapes CI.
5. Dans les rapports, séparer nettement : `sémantique confirmée`, `projection GLB confirmée`, `contact numérique confirmé`, `QA vision des rendus confirmée`. Aucun statut ne préjuge du suivant.

**Règle d'arbitrage :** si une implémentation contredit ce plan, arrêter la dérive, documenter pourquoi et corriger le flow. Ne pas improviser une nouvelle heuristique sur l'objet.
