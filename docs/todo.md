# WarConquer — TODO : personnages vivants et personnalisables

> **Statut :** idées à explorer, non implémentées et non priorisées, sauf la section « Plus tard ». Ce document complète la [bible du jeu](game-bible.md), le [pipeline de personnages et d'équipements](character-production-pipeline.md) et le [Character Lab](character-lab.md). Les choix techniques ci-dessous sont des pistes, pas des décisions figées.

## Apparence et équipement

- [ ] **Accessoires et objets portés par les personnages.** Permettre à une unité d'ajouter ou de retirer des éléments visibles sur son corps : bracelets, chapeaux, bijoux, sacs, protections, etc. Étendre le système de sockets/ancrages du rig au-delà des armes tenues en main, avec une gestion des superpositions, des déformations éventuelles et de la compatibilité avec les animations.
- [ ] **Variantes de couleurs par unité sans modifier le mapping UV.** À partir d'une même texture et d'un même modèle 3D, permettre de changer indépendamment la couleur des vêtements, objets, peau, yeux et cheveux pour une unité précise. Étudier des masques de régions, des paramètres de matériaux ou des shaders de recoloration, en préservant les coordonnées UV, les détails et l'atlas d'origine.

## Perception du terrain, déplacements et mémoire

- [ ] **Reconnaissance rapide et intelligente du terrain, assistée par LLM.** Un système peu lent et peu coûteux doit interpréter ce que chaque personnage peut voir de la carte : chemins, obstacles, passages, relief, dangers, ressources, autres unités et points d'intérêt. Il doit aider le personnage à s'orienter et à choisir des initiatives de déplacement pertinentes.
  - Conserver une **mémoire spatiale individuelle** : endroits déjà vus, observations, changements constatés et incertitudes, en respectant le brouillard de guerre et les limites de perception.
  - Étudier une approche hybride : géométrie/navigation déterministe pour les trajets précis, reconnaissance et raisonnement contextuel pour les décisions, avec cache et actualisations sur événements pour éviter un appel LLM à chaque frame.

## Pensée, dialogue et ordres

- [ ] **LLM économique pour penser, décider et parler.** Donner aux personnages une capacité légère de raisonnement contextuel, de dialogue et d'initiative, alimentée par leurs ordres, objectifs, observations, souvenirs et état émotionnel. Ce système doit pouvoir **déléguer des intentions de déplacement** au module de reconnaissance/orientation du terrain, sans prendre directement le contrôle de la navigation précise.
  - Prévoir des budgets de latence/coûts et une fréquence d'activation adaptée : les personnages n'ont pas tous besoin d'un appel LLM continu.
  - Définir les limites de l'autonomie pour que les initiatives demeurent compatibles avec les ordres du joueur et les règles du RTS.
- [ ] **Ordres « en mode dieu » et communication avec le joueur.** Le joueur donne des directives de haut niveau à ses personnages. Lorsqu'un personnage rencontre un problème qu'il ne peut résoudre seul (obstacle, manque de ressources, conflit d'ordres, danger, etc.), il peut faire apparaître un **avatar à l'écran** pour expliquer la situation, demander de l'aide ou proposer des solutions. Prévoir un mécanisme pour éviter les sollicitations incessantes.

## Voix, émotions et réactions immédiates

- [ ] **Synthèse vocale expressive (TTS).** Donner une voix aux dialogues générés par les personnages, capable d'exprimer différentes émotions (peur, joie, colère, inquiétude, soulagement, etc.), avec une identité vocale cohérente pour chaque personnage et un coût d'utilisation maîtrisé.
- [ ] **Cris et réactions vocales liées aux émotions immédiates.** Relier des exclamations, cris, halètements ou réactions brèves aux émotions provoquées directement par les événements et par le système de perception/déplacement (surprise, menace rencontrée, effort, fuite, douleur, etc.). Étudier un chemin de réaction plus rapide que le dialogue LLM complet, tout en conservant une cohérence émotionnelle.

## Besoins et état des personnages

- [ ] **Besoins physiologiques et soins.** Étudier des personnages qui peuvent réellement avoir besoin de guérison, de nourriture, de sommeil et de récupération. Les besoins doivent influer de façon intelligible sur leur comportement et leurs demandes, sans introduire une micogestion excessive incompatible avec la [lisibilité du RTS](game-bible.md).

## Plus tard — nice to have

- [ ] **Émergence contextuelle d'objets simples.** Certaines situations ou actions pourraient faire apparaître ou produire des objets simples cohérents avec le contexte. Préciser ultérieurement les règles de création, leurs propriétés, leur persistance et leur intérêt concret pour le jeu.

## Articulation envisagée des systèmes

1. **Monde visible → perception et mémoire :** les observations du terrain et les événements enrichissent ce que chaque personnage sait ou croit savoir.
2. **Ordres du joueur + besoins + mémoire → LLM de décision/dialogue :** le personnage interprète la situation et choisit une intention ou une réponse.
3. **Intentions → orientation et navigation :** le système de terrain propose une voie et le moteur de déplacement l'exécute dans les règles physiques du jeu.
4. **Événements et émotions → voix :** les réactions urgentes peuvent être immédiates; les paroles construites passent par le TTS expressif.
5. **Blocage non résolu → avatar joueur :** le personnage remonte une difficulté et sollicite une décision du joueur.

**Principe à conserver :** distinguer la perception, la décision, la navigation, l'expression et le rendu visuel. Les modèles génératifs enrichissent le comportement, mais le moteur de jeu reste responsable des déplacements, des contraintes physiques et de l'application des règles.
