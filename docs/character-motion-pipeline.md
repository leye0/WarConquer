# WarConquer – un personnage → 8 directions Muse → 8 vidéos

Ce pipeline historique pour les huit images Muse puis huit vidéos OpenRouter est conservé tel quel. Il est **distinct** du nouveau [guide de pose déterministe](pose-guided-asset-animation.md), qui ne génère aucun personnage ni vidéo payante. Ne pas utiliser le workflow huit directions pour une validation de guide de pose SW.

Un seul pipeline réutilisable sous `main`, avec fichier de requête `character-motion-request.json`.

## Entrée
- `character_id` : nom du personnage / dossier de sortie (ex. `marches_hache`).
- `run_id` : identifiant unique de version; **ne pas réutiliser le même ID avec un prompt modifié**.
- `concept_path` : concept PNG existant dans `assets/concepts/`.
- `appearance`, `equipment`, `handedness`, `attack_motion` : description spécifique au personnage.
- `budget_usd` : plafond de dépenses prévisionnel; 2,00 $ US pour huit clips Grok Lite + huit images Muse, à vérifier avec les montants réels.
- `video_model` : `x-ai/grok-imagine-video-1.5-lite` (un seul modèle par tentative, aucun fallback payant automatique).
- `directions` : N, NE, E, SE, S, SW, W, NW.

## Étape 1 : Muse – 8 vues **immobiles**, une par orientation

On génère N, E, S et W en premier, puis les diagonales NE, SE, SW et NW **à partir des deux cardinales voisines** + concept original.

**Règle majeure :** la direction doit correspondre à la rotation de l'ENSEMBLE du corps : tête, épaules, sternum, bassin, jambes, genoux, pointes des deux bottes et équipements. Ne jamais seulement tourner la tête ! Le NW reprend explicitement le correctif déjà testé : rotation intégrale de 45° entre N (dos) et W (profil gauche); pas un torse vers l'Est.

Sortie dans `assets/experiments/character-motion/<character_id>/<run_id>/stills/{N,NE,E,SE,S,SW,W,NW}.png`. Chaque image est accompagnée d'un JSON détaillant son prompt, le modèle, le détourage, les références, le SHA et les coûts réels. `review-8-directions.png` permet d'inspecter les huit images ensemble.

**Les directions ne sont pas approuvées automatiquement :** un modèle peut toujours se tromper d'angle. Ce pipeline réalise le processus complet demandé, mais la planche reste à examiner.

## Étape 2 : OpenRouter vidéo – une vidéo pour CHACUNE des huit directions

Modèle image-to-video à bas prix `x-ai/grok-imagine-video-1.5-lite`, 480p, 1:1, 8 s sans audio, première frame dérivée directement du PNG de cette direction.

Cadrage inspiré du correctif SW v2 : la référence vidéo fait 768×768, personnage ne dépassant pas 35 % de sa hauteur et larges marges pour conserver l'arme au complet. **Interdiction de zoom/recentrage** dans le prompt. Il faut éviter l'arme coupée durant les attaques.

Pour CHAQUE direction, temporellement et spatialement :
- **0–4 secondes** : marche dirigée vers la bonne direction, avec jambes alternées, déplacement limité à ~5 % de l'image; orientation du corps inchangée.
- **4–8 secondes** : stop net, pieds plantés, attaque dirigée vers la même direction.
- Caméra fixe, arme complète dans l'image, aucune autre direction.

Chaque résultat est `videos/<direction>/walk-then-attack.mp4` + `contact-sheet.jpg` (huit images extraites) + `reference-768.png` + `job.json` avec coût et QA.

Les rapports détectent seulement quelques anomalies possibles (arme touchant un bord, dérive d'échelle, scènes manquantes). **Ils ne prouvent pas** la conformité du mouvement et ne remplacent pas la vérification du MP4.

## Reprise et contrôle des dépenses

La GitHub Action commit les données sur `main` **après chaque image Muse**, puis **immédiatement après chaque soumission vidéo acceptée**, avant d'attendre le résultat, et enfin après récupération du MP4. Ainsi, relancer la même requête ne doit pas engendrer un deuxième paiement pour le même fichier ou job accepté.

Un job vidéo accepté reçoit un ID stocké dans `job.json`. En cas de panne, on reprend le même ID. Aucune régénération payante automatique après erreur ou timeout d'un job accepté. Les soumissions sans confirmation sont marquées ambiguës et nécessitent une inspection humaine avant retry. Budget prévisionnel conservateur 0,22 $ par vidéo; dépenses réelles rapportées par OpenRouter. Le contrôle de budget ne garantit pas que le fournisseur ne modifiera pas ses prix, donc vérifier la facture réelle.

Si les huit images Muse ne sont pas produites, les vidéos ne démarrent pas. Chaque exécution exige un nouveau `run_id` si on change de design ou de prompt. Le répertoire des anciennes expériences reste intact pour comparaison.

Le workflow s'exécute via `.github/workflows/character-motion.yml` (push du fichier de demande ou lancement manuel). Les fichiers PHP/JS/HTML et le générateur Muse original ne sont pas modifiés.
