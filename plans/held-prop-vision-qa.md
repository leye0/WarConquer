# Plan de référence — objets tenus : vision, articulations et QA par poses

**Statut : décision d'architecture et protocole de validation, pas une preuve que la hache fonctionne.**  
**Date : 2026-10-28**  
**Portée :** tout objet avec action tenu par un personnage (hache, arc, bouclier, fusil, outil, etc.), toutes les unités et tous les clips Mixamo.  
**Complément :** [contrat technique existant](../docs/prop-interaction-contract.md).
**Vocabulaire contractuel obligatoire :** [affordances, états, contacts, contraintes et 26 scénarios](held-object-affordance-contract.md). Les rôles/fonctions de l'objet et les contraintes dépendant de son état sont deux domaines distincts; aucune règle par nom d'arme.

## Résultat attendu

Un personnage tient réellement l'objet au bon endroit, avec la ou les mains attendues, dans les poses de repos, de déplacement et d'action. La partie fonctionnelle de l'objet (tranchant, bouche du canon, corde de l'arc, surface d'impact...) est correctement orientée selon l'intention de l'action. Un verdict « prêt » doit être démontré sur des rendus **réels** et des mesures des articulations animées, pas inféré de tests unitaires qui passent.

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

- Lire les paumes, poignets, coudes, épaules et leurs positions **à l'instant réel du clip Mixamo**.
- Ajuster la transformation rigide de l'objet pour la prise principale et la direction d'action confirmée. En mode deux mains, résoudre/contrôler le deuxième contact avec une IK soumise aux longueurs et limites des membres.
- Ne pas modifier les données source Mixamo pour maquiller un résultat. Si le clip est incompatible avec les prises exigées, le rejeter ou choisir explicitement un autre rôle de clip compatible.

### 4. Tester par images fixes et mesures 3D

Pour chaque mode requis, sélectionner **des instants déterministes et conservés** :
- repos/transport : plusieurs poses significatives;
- marche et course : plusieurs phases du cycle, dont les positions extrêmes des bras;
- action : départ, préparation, armement, phase médiane, impact/effet, récupération, retour au repos;
- autres modalités : instants où chaque prise doit apparaître/disparaître.

À **chaque** instant :
1. Capturer le personnage et l'objet dans le véritable renderer, au moins de face, de côté et en trois-quarts lorsque nécessaire.
2. Générer au besoin une version **annotée** (IDs, régions, paumes, articulations, direction d'action) et une version **non annotée**, pour ne pas tromper l'évaluation visuelle.
3. Mesurer en 3D, avec des tolérances définies et testées relativement à l'échelle réelle : distance de chaque paume à sa prise attendue, faisabilité des bras, collisions et orientation de la partie active.
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
- [ ] Les retours de tests et les rendus ont été inspectés (pas uniquement le statut vert d'une Action).
- [ ] Les cas ambigus/incompatibles restent explicitement rejetés, avec preuve et cause; aucune réussite n'est annoncée sans rendu convaincant.

## Ordre de travail et discipline

1. Terminer **une seule unité pilote et ses modes** de bout en bout avec images et mesures concluantes, avant d'élargir le pipeline.
2. Ne pas ajouter une nouvelle abstraction, règle ou service sans démontrer quelle défaillance observée il corrige.
3. Réutiliser la mécanique existante de captures Character Lab/WebSuite et les contrats existants; limiter le travail périphérique.
4. Mesurer l'avancement par **poses réellement validées**, pas par nombre de fichiers, commits, tests verts, appels OpenRouter ou étapes CI.
5. Dans les rapports, séparer nettement : `sémantique confirmée`, `projection GLB confirmée`, `contact numérique confirmé`, `QA vision des rendus confirmée`. Aucun statut ne préjuge du suivant.

**Règle d'arbitrage :** si une implémentation contredit ce plan, arrêter la dérive, documenter pourquoi et corriger le flow. Ne pas improviser une nouvelle heuristique sur l'objet.
