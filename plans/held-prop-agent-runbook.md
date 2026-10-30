# Guide de reprise pour agents — préhension 3D objet × personnage × Mixamo

> **À lire avant de modifier le pipeline.** Ce document indique **où reprendre**, **quels fichiers toucher**, **ce que produire** et **comment démontrer qu'une case est réellement terminée**. La feuille de route officielle et les cases A1–H5 sont dans [held-prop-vision-qa.md](held-prop-vision-qa.md). Le sens physique des champs est défini dans [held-object-affordance-contract.md](held-object-affordance-contract.md). Les consignes générales du dépôt sont dans [AGENTS.md](../AGENTS.md).
>
> **Ce document ne certifie aucune prise.** L'état de la hache est **VISUAL_NO_GO**. Ne pas traduire un `contact-numeric-verdict.json: approved` en « l'objet est tenu ».

## 1. Point de reprise exact, sans connaître la conversation

- **Dépôt :** `leye0/WarConquer`. **Branche de référence après intégration :** `main`; [PR #2](https://github.com/leye0/WarConquer/pull/2) conserve l'historique de la branche expérimentale `feat/semantic-prop-contact-contract`. Pour les prochains correctifs, partir de `main` à jour sur une branche dédiée, sauf demande explicite du propriétaire. **Une fusion du WIP sur demande n'équivaut pas à un `GO`** et ne donne pas le droit d'annoncer une préhension résolue.
- **Pilote obligatoire :** unité `marches_hache`, objet `axe`, GLB réel `assets/experiments/props/marches_hache/trellis-v1/axe.glb`.
- **Contrat source :** `assets/experiments/props/marches_hache/trellis-v1/interaction-contract.json`. La vision a nommé `grip_lower_haft` (main droite principale), `grip_upper_haft` (main gauche secondaire), `axe_head` (tranchant), et les modes `carry_mode` / `use_mode_chop`. Le rôle Mixamo `axe_chop` est un **candidat**, pas une compatibilité prouvée.
- **Plan de repères actuel :** `assets/experiments/props/marches_hache/trellis-v1/grip-plan.json`. `mesh_landmarks.schema = 1`; les prises `local` portent la méthode `vision-nearest-surface` (un **sommet proche**, pas une surface de saisie). Le champ `visual_qa.status` est **`rejected`**; les deux juges visuels refusent la prise à deux mains même quand `numeric_issues` est vide.
- **Raison diagnostiquée :** `scripts/prop-mesh-landmarks.py::project_labelled_vertex` et `scripts/audit-prop-vision-regions.py::reconcile_physical_regions` réduisaient la délimitation vision à un sommet; la réparation automatique est maintenant interdite; `scripts/character-lab-client.js::importedPropLandmarks` remappe sur un sommet importé. Le `palmFrame` calcule déjà une orientation, mais `temporarySecondaryIK` ne résout que bras/avant-bras, **ni le poignet ni les doigts**.
- **Autre lacune observée :** `scripts/capture-prop-contact.mjs` échantillonne les **huit poses de frappe** par fractions explicites de la timeline Mixamo, mais la marche/course sont capturées après des `sleep(500)` : ce n'est **pas encore** un échantillonnage déterministe de leurs phases animées.
- **Statut honnête :** sémantique source **documentée**; rendu GLB et captures **existants**; surface de contact 3D **non confirmée**; prise orientée et doigts **non résolus**; action **VISUAL_NO_GO**; généricité **non démontrée**.

**Reprise technique immédiate : vérifier les prérequis B2–B4, puis réaliser B5–B8** (2D vision → vrais triangles visibles → zone de surface stable → vérification multiangles). **Ensuite seulement : C3–C7, D2–D9, F2–F7, G3–G9, H1.** Ne pas multiplier les rotations heuristiques pour faire passer une métrique à deux points.

## 2. Comment commencer chaque session

1. Lire dans cet ordre : `AGENTS.md`, ce guide, `plans/held-prop-vision-qa.md`, `plans/held-object-affordance-contract.md` et `docs/prop-interaction-contract.md`. Respecter les instructions supplémentaires applicables aux fichiers modifiés.
2. Vérifier la branche, les changements non committés, la PR et les **derniers** reçus/CI. Les statuts ci-dessus sont un instantané : une autre session peut avoir avancé entre-temps.
3. Lire les cases A1–H5 et **choisir le premier critère bloquant dont les prérequis sont satisfaits**. Une case `[x]` exige les preuves indiquées au §7; si la preuve manque, la rouvrir.
4. Identifier **une défaillance observée**, le contrat concerné et le test qui la reproduit **avant** d'écrire un correctif.
5. Modifier le chemin de production **existant**; éviter un second solveur ou des données « de démonstration » qui ne sont pas consommées par Character Lab. Préserver les anciens reçus/empreintes et prévoir une migration de schéma explicite.
6. Lancer les tests hors ligne pertinents, puis les rendus réels. Ouvrir les PNG et conserver les échecs. Si un outil, un accès ou un modèle bloque, consigner la cause et rester `needs_review`.
7. Ne cocher que les cases prouvées; actualiser le journal de reprise (§8) et expliquer précisément à l'utilisateur ce qui reste `NO_GO`.

**Le prochain agent doit commencer par une vérification B2–B4, pas par une nouvelle optimisation de pose de la hache.**

## 3. Carte des fichiers et des responsabilités réelles

| Fichier | Responsabilité actuelle / point à vérifier |
|---|---|
| `assets/experiments/props/marches_hache/trellis-v1/interaction-contract.json` | IDs de parties et de prises, modes, côtés des mains, signification de l'action; **ne pas réinventer ces rôles** |
| `assets/experiments/props/marches_hache/trellis-v1/grip-plan.json` | Repères GLB `mesh_landmarks` historiques et reçus/rejets de QA; **ne pas le traiter comme un schéma de surface déjà valide** |
| `scripts/prop-mesh-landmarks.py` | `glb_geometry`, `make_views`, `validate_answer`, `project_labelled_vertex`, `lift_named_landmarks` : génération de vues du GLB texturé, réponse vision et projection actuelle **sommet le plus proche** |
| `scripts/audit-prop-vision-regions.py` | `audit_multiview`, `validate_multiview`, `reviewed_regions` : quatre vues complètes, IDs sémantiques, directions et contrôle indépendant des surimpressions; ancien audit disponible seulement avec `--legacy-crops`; réparation par sommet interdite |
| `scripts/test-prop-mesh-landmarks.py` | Tests de projection et de sens signé. **Attention : certains tests exigent encore `vision-nearest-surface`**; les remplacer par des assertions sur de vrais triangles, pas seulement supprimer l'assertion gênante |
| `scripts/test-audit-prop-vision-regions.py` | Tests des boîtes natives/coordonnées normalisées, re-projection et interdiction d'inventer un label |
| `scripts/rig-contact-landmarks.js` | `palmFrame` : paume, normale, direction des doigts, axe transversal; **valider les signes anatomiques** |
| `scripts/character-lab-client.js` | `importedPropLandmarks`, `findGripAnatomy`, `temporarySecondaryIK`, `alignTwoHandCarry` : point de montage réellement utilisé par la scène Babylon; le code actuel n'oriente pas le poignet/la préhension |
| `scripts/prop-motion-contact.js` | `solveTwoGrips`, portée des membres, géométrie/IK d'appoint; un résidu positionnel n'est pas un contact de surface complet |
| `scripts/capture-prop-contact.mjs` | Captures du vrai navigateur, `contact-motions.json`, `contact-numeric-verdict.json`, gros plans; marche/course non encore échantillonnées sur un `goToFrame` déterministe |
| `scripts/verify-prop-visual-qa.py` | Analyse OpenRouter indépendante des captures, boîtes labellisées et verdict structuré; un modèle conversationnel ne garantit pas implicitement un détecteur natif : vérifier **ses boîtes produites** |
| `scripts/run-prop-visual-qa.py` | Orchestration des deux juges, agrégation `GO/NO-GO`, refus en cas d'échec numérique **ou** visuel |
| `.github/workflows/feature-held-prop-pose-qa.yml` | Rejoue tests, Babylon et modèles vision; **les filtres `paths` n'incluent pas actuellement `prop-mesh-landmarks.py` ni `audit-prop-vision-regions.py`** : mettre à jour le déclenchement ou lancer explicitement le workflow lors des changements de projection |
| `.github/workflows/websuite.yml` et `docs/websuite.md` | QA visuelle WebSuite pour les modifications HTML/JS; ouvrir les images produites, pas uniquement la page de statut |

Si un nom de fichier, un contrat ou une fonction diffère sur la branche au moment de reprendre, **inspecter le code actuel** et modifier le guide avant d'agir.

## 4. Contrat d'entrée / sortie de la prochaine étape B2–B8

### Entrées obligatoires

- **Sémantique vérifiée :** pour chaque ID, rôle (`grasp_region`, `active_surface`, `outlet`, etc.), main/contact/mode attendu, direction signée et source d'autorité. Les IDs de la hache viennent de `interaction-contract.json`.
- **Vision sur le GLB texturé :** images **réellement soumises au modèle**, boîtes/polygones/masques avec label exact, crop et conversion des pixels, vue/caméra, version du modèle et reçu brut. Une boîte n'est pas valide si elle délimite seulement du fond ou un autre élément.
- **Géométrie mesurée :** GLB et empreinte, hiérarchie des nœuds, positions/indices des **triangles**, transforms de mesh, projection orthographique/perspective et profondeur/rayons de chaque vue. Pas de coordonnées déduites de la longueur de l'objet.
- **Ambiguïtés :** occlusion, épaisseur cachée, transparence, symétrie, signes de normales ou de direction non observés ⇒ vue supplémentaire ou `needs_review`.

### Sortie requise : contrat de surface versionné

Le format ci-dessous est une **interface cible à implémenter**, **pas** un schéma v2 déjà présent dans le runtime. Ne pas renseigner des valeurs de démonstration dans un reçu de production :

```ts
type ContactSurfaceV2 = {
  schema: 2;
  glb_sha256: string;
  part_id: string;              // ID validé en amont, jamais inventé par géométrie
  role: string;
  evidence: Array<{
    image_sha256: string;
    view_id: string;
    camera_id: string;
    region_kind: "bbox" | "polygon" | "mask";
    region: number[];           // Coordonnées avec convention et crop documentés
    model_response_sha256: string;
  }>;
  patch: {
    mesh_node: string;
    primitive: number;
    triangles: Array<{
      triangle_id: number;
      barycentric_contact: [number, number, number]; // sur la face, non un sommet arbitraire
    }>;
    accessible_width: number | null;
  } | null;
  contact_frame: {
    position_local: [number, number, number];
    normal_local: [number, number, number];
    tangent_local: [number, number, number];
    sign_evidence: string;      // source de "dessus/dehors/tranchant"
  } | null;
  projection_error_px: number | null;
  status: "confirmed" | "needs_review";
  missing_evidence: string[];
};
```

**Invariants :**

1. `confirmed` implique **un vrai triangle**, des coordonnées barycentriques valides, un point intérieur à la **région étiquetée** et une projection à erreur contrôlée; la zone de prise peut couvrir **plusieurs** faces. Une position 3D « près » d'une boîte n'est pas suffisante.
2. La position, la normale et la tangente sont dans **un même repère explicite** `object_local`; le rendu reconstruit la position dans Babylon via les transforms réelles, sans recherche du sommet le plus proche.
3. La **géométrie** calcule une normale; **la vision/les données source** indiquent de quel côté se trouvent la paume, la sortie, le tranchant ou le dessus. Une normale de triangle non signée sémantiquement ne suffit pas.
4. Une seule vue ne prouve pas les faces cachées : faire appel à une autre vue, signaler l'ambiguïté ou rejeter. Une région initiale rejetée **n'est jamais déplacée silencieusement** au centre d'une boîte pour créer un faux repère accepté.
5. Si le GLB original, les images, le prompt ou le mode changent, les reçus et repères associés deviennent **périmés**; les empreintes rendent les incohérences observables.
6. Conserver les reçus `schema: 1` et les annotations payées; **migration explicite** vers le nouveau lecteur. Aucun ancien test de sommet ne peut faire passer un contrat de surface.

### Démonstration attendue pour cocher B5–B8

- `B2–B4` : une surimpression vision de **chacun des `part_id` requis**, visible et vérifiable sur au moins deux vues utiles du GLB texturé, avec contradictions traitées.
- `B5` : tests de raycast/déprojection sur triangles réels; rejet boîte sur vide, derrière l'objet ou sur une face non visible; vérification d'indices et coordonnées barycentriques.
- `B6–B7` : un **patch** accessible et un repère local orienté pour chacune des deux prises et le sens de l'action; pas un unique `local` tiré d'un vertex.
- `B8` : reprojections **identiques** depuis les mêmes points 3D sur plusieurs caméras et captures PNG où surfaces, normales/tangentes et IDs se trouvent sur la bonne pièce. Vision indépendante confirme les surimpressions.
- **Verrou :** tant que ces artefacts sont absents ou contestés, **aucune** case B5–B8 n'est cochée, même si un test unitaire affiche `PASS`.

## 5. Étapes suivantes : livrable et test bloquant

| Cases officielles | Travail ciblé / sortie | Test ou preuve obligatoire |
|---|---|---|
| **B2–B4** | Régions annotées, crop/boîtes, IDs cohérents entre vues | PNG originaux + boîtes; refus d'une boîte hors objet; relecture indépendante |
| **B5–B8** | Triangles visibles, barycentriques, zone/repère 3D signé; lecteur Babylon | Tests de raycast et re-projection; PNG multiangles avec patches/axes |
| **C3–C7** | `palmFrame` gauche/droite calibré, os du pouce et doigts, dimensions/limites du vrai rig | Rendus des paumes et os; test de normale inversée et rig sans doigts |
| **D2–D5** | Ajustement **couplé** objet, bras, poignets et fermeture des doigts quand possible | Paume retournée 180° à centre correct ⇒ `NO_GO`; main flottante ⇒ `NO_GO` |
| **D6–D9** | Collisions, limites, contacts distincts et rejet d'un clip impossible | Tests de pénétration, portée, main intervertie, conflit entre deux prises |
| **E2–E6** | Contacts/modes/fonctions sur vraies frames Mixamo; marche/course aussi sur frames exactes | Timelines documentées, mêmes instants rejouables, transitions et direction fonctionnelle |
| **F2–F7** | Mesures surface+angle+doigts+état, seuils physiques justifiés et contre-exemples | Régressions adversariales qui **échouent** correctement, indépendamment du VLM |
| **G3–G9** | Captures brutes + annotées, boîtes VLM, métriques et décisions lisibles par pose | Deux regards indépendants; aucun `GO` si une main/partie reste ambiguë |
| **H1** | Hache réellement tenue à deux mains en transport, marche/course et frappe | **Toutes** les poses critiques : métriques conformes **et** deux `VISUAL_GO` sur vrais PNG |
| **H2–H5** | Pot rempli/vidé, fusil, arc, bouclier, lanterne, puis 26 scénarios | Preuves par mode/état; pas de règles par nom d'objet dans le solveur |

**Règle de travail :** avancer au rythme de ces validations, pas au nombre de commits. Une correction d'une phase ultérieure qui contourne un prérequis non satisfait ne ferme aucune case.

## 6. Reproduction des tests et de la QA

À exécuter depuis **la racine du dépôt**, avec Python 3.11, Node, `Pillow` et `numpy` selon les dépendances du workflow. Ne pas improviser des versions si le workflow en épingle; vérifier l'environnement et les instructions CI.

```bash
python scripts/unit-pipeline.py status --unit marches_hache
python scripts/test-prop-interaction-contract.py
python scripts/test-prop-mesh-landmarks.py
python scripts/test-audit-prop-vision-regions.py
python scripts/test-verify-prop-visual-qa.py
python scripts/test-prop-visual-qa.py
node scripts/test-prop-motion-contact.mjs
node --check scripts/capture-prop-contact.mjs
```

Les tests existants servent de **socle**, mais plusieurs ne mesurent encore que des positions de points/sommets. Un correctif B5–B8 doit ajouter des tests spécifiques aux **triangles, patches et normales**, et mettre à jour les assertions historiques de `vision-nearest-surface` sans les neutraliser.

Pour l'essai navigateur + modèles vision, utiliser la chaîne de `.github/workflows/feature-held-prop-pose-qa.yml`. Elle installe Babylon, sert `character-lab.html`, capture les frames et lance :

```bash
python scripts/run-prop-visual-qa.py \
  --unit marches_hache \
  --output /tmp/wc-held-prop-qa \
  --passes primary,independent \
  --allow-paid
```

Ce dernier appel est **payant**, exige `OPENROUTER_API_KEY` configurée pour le workflow, un serveur Character Lab réel et un navigateur disponible; **le lancer seulement quand les nouvelles sorties peuvent être évaluées**. Réutiliser les reçus mis en cache si les entrées et le modèle/prompt sont identiques; ni plafond historique arbitraire, ni retries aveugles.

Les principaux artefacts attendus sont :

- `contact-motions.json`, `contact-numeric-verdict.json`, `contact-state.json` dans le dossier de captures;
- PNG `front`, `side`, `back`, `walk`, `run`, `action`, `action_mid...` et `*_grip` (versions rapprochées);
- JSON des deux verdicts `visual_qa.reviews`, incluant les boîtes/labellisations et **leurs échecs**;
- nouveaux PNG des régions/patches 3D multiangles et reçus associés pour B5–B8.

**Important :** la GitHub Action d'équipement actuelle ne se déclenche pas automatiquement pour tous les scripts de projection. Mettre à jour son filtre `paths` au moment de changer ces scripts, ou déclencher la validation équivalente explicitement. Pour toute modification visuelle HTML/JS, satisfaire **aussi** la règle WebSuite de `AGENTS.md` et **ouvrir** le PNG généré. Ne jamais présenter un statut CI vert comme substitut de l'inspection.

## 7. Règle formelle pour cocher une case

Chaque case cochée dans `held-prop-vision-qa.md` doit pouvoir être reliée à :

1. **Entrées vérifiables** : identifiants exacts de GLB, personnage, mode, clip, versions et empreintes sources.
2. **Résultat démontré** : changement de production réellement consommé par Character Lab (pas un prototype isolé).
3. **Tests pertinents** : commande, issue et au moins un test adversarial lorsque la case porte sur un invariant.
4. **Preuves visuelles** pour toutes les cases de projection, posture ou animation : vrais PNG ouverts et inspectés, annotations et vues identifiées.
5. **Décision indépendante** si la case porte sur une prise validée : mesures 3D **et** vision; avis `NO_GO` ou `unresolved` ⇒ case ouverte.
6. **Traçabilité** : commit/PR, liens ou chemins vers les reçus, date, limites et prochaine tâche.

Statuts à conserver **séparément** : `semantic_status`, `glb_surface_status`, `anatomy_status`, `numeric_pose_status`, `independent_vision_status`, `overall_status`. Les anciennes valeurs comme `semantic_status: confirmed` n'impliquent **aucun** des statuts suivants.

Si une case avait été cochée sur une preuve insuffisante (ex. marche/course non déterministes), **la rouvrir** ou restreindre très précisément ce qui a été démontré. Ne jamais « arranger » un test visuel en masquant un contact problématique, en changeant de cadrage favorable ou en relaxant une tolérance sans justification physique.

## 8. Journal de reprise et format de compte rendu

À la fin de chaque session, ajouter une entrée courte et datée **dans la PR ou dans le journal de travail associé**, sans remplacer les anciens reçus ni écraser un refus :

```text
Date et branche :
Cases ciblées / prérequis :
Défaillance réelle constatée :
Fichiers et contrats modifiés :
Entrées vérifiées (GLB, personnage, clip, modèles, empreintes) :
Tests lancés, résultat exact :
Captures PNG ouvertes, vues/frames, résultat :
Verdicts numériques / OpenRouter indépendants :
Cases cochées [x] / encore ouvertes [ ] :
Cause de blocage éventuelle :
Première tâche exacte pour l'agent suivant :
Commit / PR / chemins des artefacts :
```

**Exemple d'entrée honnête, avant correction :** `B5–B8 [ ]`; sémantique hache documentée; sommets `vision-nearest-surface` encore utilisés; erreurs de paume ponctuelles mesurées, mais les deux modèles OpenRouter ont retourné `VISUAL_NO_GO` à la prise. **Prochaine tâche : vérifier B2–B4 puis reconstruire la projection sur triangles, sans modifier le rôle des deux prises.**


### Reprise du 2026-10-29 — B2–B4, régions sur vues complètes

- Branche : `fix/held-prop-multiview-regions`, base `53a831c`, implémentation `ffeb82b`.
- Défaillance reproduite : l’ancien audit utilise une seule vue et des crops centrés sur des sommets contestés; son reçu `studio_flash_native3` annonçait `confirmed` malgré `grip_upper_haft.visible=false`. Ce reçu historique est conservé, pas considéré comme une preuve B2–B4.
- Correction : le chemin par défaut de `audit-prop-vision-regions.py` demande chaque ID du contrat sur quatre images complètes; aucune ancienne coordonnée ne sélectionne une région. Le prompt sépare la surface fonctionnelle de son support et permet à l’origine de direction de se trouver hors de la boîte de l’effet. Les deux points restent obligatoirement sur des pixels du GLB.
- Relecture : modèle distinct sur les images brutes et leurs surimpressions; deux vues visibles confirmées au minimum par ID, contradictions conservées et demandes de vues supplémentaires bloquantes. Deux requêtes au maximum par exécution, sans retry automatique, cache par empreinte et réponses fournisseur brutes/coûts sauvegardés avant parsing.
- Migration : `mesh_region_review.schema=2`, `status=confirmed_2d|needs_review`. Aucun changement des sommets `mesh_landmarks`, du solveur ou du verdict de pose. `confirmed_2d` n’est pas une surface B5 ni une prise validée. Le dossier dépend des empreintes des images, sources, prompts et modèles.
- Preuves locales : `assets/experiments/props/marches_hache/trellis-v1/vision-region-receipts/multiview-full_views_v2-d7e94524c56a4d25/` : quatre PNG réellement rendus du GLB, tous ouverts, `inputs.json` avec empreintes et projection/caméras. Vues 0/1 étroites; vues 2/3 montrent les deux faces. Aucune annotation modèle nouvelle à ce stade.
- Tests réussis : `test-prop-interaction-contract.py`, `test-prop-mesh-landmarks.py`, `test-audit-prop-vision-regions.py`, `test-prop-visual-qa.py`, `test-verify-prop-visual-qa.py`, `test-prop-motion-contact.mjs`. Régressions ajoutées : IDs/vues absents ou dupliqués, région/direction sur fond, moins de deux vues utiles, contradiction indépendante, sortie malformée conservée sans second paiement.
- Blocage : publication GitHub refusée par la revue automatique d’autorisation; aucun essai OpenRouter/CI nouveau, aucune PR créée. Le workflow spatial est préparé pour cette branche et le marqueur `[spatial-pilot:marches_hache]`.
- Cases : B2–B4 restent ouvertes, B5–B8 inchangées; pilote toujours `VISUAL_NO_GO`. La vérification multi-vues est sémantique en 2D : l’ambiguïté de profondeur devra aussi être mesurée en B5.
- Prochaine action : après autorisation de publier cette branche, lancer le workflow spatial, ouvrir les quatre overlays et lire les deux reçus. Corriger les régions contestées ou demander les vues manquantes avant de commencer B5; ne pas réutiliser `confirmed` du reçu historique.


### Résultats CI du 2026-10-29 — PR #5

- Publication autorisée explicitement par le propriétaire et effectuée : [PR #5](https://github.com/leye0/WarConquer/pull/5), branche `fix/held-prop-multiview-regions`. Le blocage de publication décrit plus haut est levé.
- Le premier modèle configuré (`qwen3-vl-32b-instruct`) a répondu HTTP 404; le catalogue OpenRouter a été vérifié et le modèle remplacé par `qwen/qwen3-vl-30b-a3b-instruct`. Les erreurs HTTP sont désormais conservées dans les reçus. L'ancien échec reste archivé.
- Le modèle 30B renvoie quatre entrées dans un tableau JSON sans enveloppe `views`. Le lecteur accepte cette variation structurelle, conserve les reçus bruts et applique exactement les mêmes contrôles aux IDs, coordonnées, pixels et directions. Aucun point déplacé. Annotation réutilisée depuis le cache lors du troisième lancement.
- [CI spatial 40858727775](https://github.com/leye0/WarConquer/actions/runs/40858727775) : six suites de tests réussies; annotation 30B et relecture 235B réellement exécutées. Coût reçu : 0,00105645 + 0,00227999 USD = 0,00333644 USD. Résultat final `needs_review`, workflow rouge attendu pour ce refus.
- Preuves : `assets/experiments/props/marches_hache/trellis-v1/vision-region-receipts/multiview-full_views_v2-c1162a3241ae0a17/` contient les quatre vues brutes, les quatre overlays, les deux réponses fournisseur, leurs coûts et `report.json`. Les quatre overlays ont été ouverts et inspectés.
- Échec observé : l'origine de direction tombe sur fond en vues 0/1; la pointe en vue 3 tombe sur fond, à gauche, alors que la tête s'étend vers la droite. Les coordonnées du tranchant sont recopiées entre les vues 2/3. Les boîtes de prise s'étendent aussi excessivement, notamment au-delà du bout visible du manche.
- Le modèle de relecture 235B confirme à tort toutes les régions/directions. Le contrôle des pixels refuse néanmoins le résultat : la partie fonctionnelle n'a qu'une vue admissible, pas deux. Les quatre confirmations de prises dans `confirmed_views` décrivent ce contrôle partiel, **pas une acceptation humaine de leurs limites**. B2–B4 demeurent ouverts; aucune surface B5 ni prise anatomique n'est validée.
- [CI Unit pipeline 40858739170](https://github.com/leye0/WarConquer/actions/runs/40858739170) réussie après adaptation de la régression : un audit de régions schéma 2 ne doit jamais certifier les anciens sommets comme surfaces 3D validées.
- Prochaine tâche précise : corriger l'annotation générique par vues indépendantes (éviter la copie de coordonnées entre vues opposées), resserrer les limites des prises et obtenir une vraie localisation du tranchant. Rejouer les contrôles des pixels et une relecture qui détecte effectivement ces contre-exemples avant B5. Ne pas déplacer les régions pour faire passer le contrôle et ne pas cocher B2–B4 sur les verdicts positifs erronés du 235B.

### 2026-10-29 — revenir à l'essai visuel concret

À la demande du propriétaire, inspecter un cas réel avant de développer davantage
l'automatisation. Aucun nouvel appel payant n'a été fait pour cet essai.

- Le renderer CPU inversait V dans l'atlas glTF : corrigé et couvert par une
  texture asymétrique et un test de rasterisation. Les reçus antérieurs restent
  archivés, mais leurs textures ne constituent pas une référence visuelle fiable.
- Le dernier essai Qwen 3.7 (`multiview-qwen37_texture_v3-c3575ae167dc9e29`)
  reste `needs_review` : les pointes de fonction des vues 0/1 sont dans le fond.
  Les vues 2/3 sont meilleures. Ne pas cocher B2–B4.
- Défaut de caméra reproduit dans Babylon : appeler `setTarget` APRÈS les angles
  recalcule alpha, beta et rayon. La vue demandée à alpha=pi/2 et rayon=3 revenait
  à alpha=-0.80949 et rayon=12.67165. Corriger l'ordre cible → angles → rayon,
  préserver aussi les angles et la limite de rayon autour des gros plans.
- `capture-prop-contact.mjs … --still` capture désormais la frame médiane exacte
  du clip de repos, sous trois angles avec gros plans. Chaque image a un JSON
  de caméra effective et de diagnostic; `inspection-pose.json` donne clip/frame.
  Commande locale/CI sans modèle :
  `node scripts/capture-prop-contact.mjs marches_hache axe assets/experiments/props/marches_hache/trellis-v1/manual-inspection-20261029 --still`.
- Inspection locale ouverte : frame 90 de `Idle_Mixamo_WithAxe`, arme horizontale
  au niveau du ventre et mains hors des prises. Le solveur refuse la pose pour
  pénétration du torse (~0.15 m). Ceci est une reproduction d'échec, PAS un
  placement manuel de référence réussi. Le script conserve les images avant
  de sortir en échec. Le contrôle des caméras, lui, retrouve les angles demandés.

Prochaine tâche concrète : utiliser ces gros plans pour établir une prise de
référence sur le vrai mesh et les vraies paumes, puis comparer le résultat
automatique à cette référence. Aucun déplacement manuel ne doit être déguisé
 en annotation de modèle ni devenir une règle spéciale d'arme. B5–B8 et les
poignets/doigts restent ouverts. Statut global : **VISUAL_NO_GO**.

### 2026-10-29 — correction de la recherche de pose, frame 90

Cause reproduite : les déplacements candidats de la paume principale ne
combinaient pas levée, avance et mouvement latéral. La recherche concluait à
une collision inévitable alors qu'une pose accessible existait. Ajout de
combinaisons dans le repère anatomique mesuré (haut/avant/droite), sans nom
 d'arme, coordonnées propres à la hache ni changement des seuils de refus.

Comparaison du même clip et de la même frame :
- avant : pénétration du torse de 0.14972 m, contacts rejetés;
- après : dégagement mesuré de 0.020 m, résidu principal arrondi à 0.000 m,
  secondaire de 0.012 m, deux bras accessibles;
- cinq instants de repos locaux (0, .25, .5, .75, 1) : résidu secondaire
  0.007–0.012 m, dégagement 0.001–0.051 m. Ce sont des métriques de proximité,
  pas une preuve de fermeture correcte des doigts ni de continuité animée.

Preuves avant conservées dans `manual-inspection-20261029/`; nouvelles captures
réelles dans `diagonal-search-inspection-20261029/`, à côté du même grip-plan.
Les gros plans montrent maintenant l'objet devant le corps et les mains
repositionnées. Il faut encore corriger/valider l'orientation des poignets et
le contact des doigts : le prototype n'est pas une préhension de surface.
Les repères 3D historiques restent contestés; aucun statut B2–B8 n'a été promu.
La marche, la course et l'action ne sont pas validées par ce correctif au repos.
