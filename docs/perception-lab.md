# WarConquer — Perception Lab

Le [Perception Lab](../perception-lab.html) réutilise l'arène isométrique du [Character Lab](../character-lab.html) : sol, quadrillage, six rochers, lumières, caméra. La scène commune vit dans [arena-scene.js](../scripts/arena-scene.js). Le Character Lab conserve ses contrôles WASD et ses animations.

## Ouverture

Démarrer le serveur existant : node scripts/serve-character-lab.mjs. Ouvrir ensuite http://127.0.0.1:4173/perception-lab.html, ou la version publiée https://www.streamlev.com/WarConquer/perception-lab.html.

Cliquer sur Ennemi, Ressource, Obstacle ou Allié, puis sur le terrain, ajoute un objet. Une fois sélectionné, modifier nom, nature, faction, quantité de ressource, points de vie des unités, danger (0–1), caractère bloquant et occultant. Les six rochers sont de vrais obstacles dans ce laboratoire. On peut effacer et recréer la démonstration.

## Contrat du cervelet

Le module [perception-brain.js](../scripts/perception-brain.js) n'a aucune dépendance et ne fait aucun appel API :

- new Brain({id, team, x, z, heading, visionRange, fov, speed, bravery, maxCells, maxEntities, memoryTtlMs})
- brain.setPose({x,z,heading}) reçoit la position réellement validée par la simulation.
- brain.step(world, order, dtMs, nowMs) renvoie {status, mode, fear, visible, goal, move:{dx,dz}, path, action, memory}.
- brain.snapshot() expose les observations et souvenirs bornés, plus tard exploitables par un LLM de décision.

Le monde contient originX, originZ, grid (lignes de points et # bloquants), occlusion (# opaques indépendants des collisions) et objects. Chaque objet possède id, kind, team, x, z, radius, blocking, opaque et éventuellement threat et resourceType.

| Ordre structuré | Effet |
| --- | --- |
| {type:"hold"} | Observer sans bouger |
| {type:"goto",x:3,z:1} | Marche directement vers ce point, avec détour si nécessaire |
| {type:"relative",direction:"left",distance:4,id:7} | Orientation relative au début de l'ordre |
| {type:"approach",entityId:"enemy-1",distance:1.2} | Se rapprocher d'une entité connue |
| {type:"find",kind:"resource"} | Chercher dans les souvenirs et explorer l'inconnu adjacent |
| {type:"flee"} | Choisir une position plus sûre |
| {type:"attack",entityId:"enemy-1",distance:1.35} | Approcher puis émettre l'intention attack |
| {type:"collect",entityId:"wood-1",distance:.95} | Approcher puis émettre l'intention collect |

Le déplacement utilise des coordonnées continues : **un ordre « aller à (x,z) » donne une direction réelle vers ce point**, sans imposer une succession de pas horizontaux/verticaux. Lorsqu'un obstacle est déjà observé, le cervelet anticipe le détour : A* à huit voisins (sans couper les angles de deux murs), suivi d'un lissage des segments praticables. Les cellules de la grille servent à la connaissance et aux collisions, pas à limiter les directions de marche. Le moteur vérifie chaque déplacement sur toute sa trajectoire, avec une marge corporelle, et peut encore le refuser si un obstacle nouvellement découvert le coupe.

Le moteur de perception prend ses décisions à **10 Hz**, tandis que la position et l'orientation du personnage sont interpolées **à chaque image** pour éliminer les sauts de 100 ms. Le [module de cadence](../scripts/perception-gait.js) lit la durée réelle des clips du GLB puis lie la fréquence des pas à la **distance physique parcourue**. La longueur d'un cycle est estimée à partir de la taille réelle normalisée du personnage (marche : 0,9 fois sa taille, course : 1,5 fois); elle reste explicitement **approximative**, et le réglage « Amplitude des pas » permet de la calibrer visuellement sans modifier le code. La vitesse de marche et de course est dérivée de cette distance par cycle et de la durée du clip, plutôt que copiée arbitrairement du Character Lab. Un personnage immobile revient à Idle. Le calcul du ramassage et des collisions reste fondé sur la position logique, pas sur la position visuelle légèrement interpolée.

La reconnaissance utilise géométrie, champ de vision, occlusion, mémoire spatiale individuelle et dernière position des objets. Les souvenirs sont plafonnés, et ceux des entités dynamiques expirent. A* planifie **uniquement sur les cellules mémorisées** en pénalisant l'inconnu, tandis que le moteur tranche les collisions réelles. La peur augmente près des ennemis, puis décroît. En mode d’ordres manuels, la peur est une information et **ne détourne plus automatiquement** l’ordre actif. La fuite s’active sur commande explicite; un futur planificateur LLM pourra aussi la décider.

## Animations réelles

Le catalogue du [serveur du Character Lab](../scripts/serve-character-lab.mjs) expose maintenant les **animations authentiques présentes dans chaque GLB**. Le Perception Lab sélectionne par défaut un modèle équipé d'un clip d'attaque (actuellement le guerrier à la hache), avec sélecteur pour changer d'unité. L'archer possède des clips Idle/Walk/Run, mais pas encore d'attaque d'arc; le lab désactive donc ses contrôles d'attaque au lieu de le laisser s'immobiliser silencieusement. Le contrôleur identifie les groupes d'animation par leur nom et déclenche marche, course pour fuir, attaque et éventuellement ramassage. Une animation de ramassage n'est reconnue que si son clip est explicitement compatible (pickup, pick_up, collect ou gather). Si elle manque, **la collecte fonctionne quand même** : la ressource disparaît du monde et sa quantité est ajoutée à l’inventaire (bois, minerai ou nourriture). Seule la gestuelle Mixamo est facultative. La transaction est exécutée une seule fois, même si le cerveau renvoie plusieurs fois la même intention. Aucune animation d’attaque n’est utilisée comme faux ramassage. Le module [perception-combat.js](../scripts/perception-combat.js) applique un vrai coup de mêlée pendant une animation authentique, à portée contrôlée (34 dégâts pour 100 PV initiaux); l'ennemi perd ses points de vie et disparaît à sa défaite. Les coups ne sont jamais fabriqués si aucun clip d'attaque n'existe.

Si le catalogue ou le modèle 3D ne peut être chargé, le laboratoire utilise clairement un avatar 3D de secours sans prétendre jouer les mouvements Mixamo.

## Vérification et limites

~~~bash
node scripts/test-perception-brain.mjs
node scripts/test-resource-inventory.mjs
node scripts/test-perception-gait.mjs
node scripts/test-perception-combat.mjs
~~~

Les tests couvrent le champ de vision, les murs, le brouillard de guerre, A* à huit directions, la marche angulaire libre, le contournement anticipé d’un mur connu sans collision, la mémoire bornée, les ordres relatifs, la peur, les positions d’interaction, les collisions refusées, l’arrêt après blocage et 100 cervelets. Les tests de ressources vérifient la collecte exactement une fois, les distances et les quantités. Les tests de cadence valident la conversion durée/distance/vitesse des clips; les tests de combat couvrent la portée, les dégâts et la défaite. La QA de navigateur [test-perception-lab-motion.mjs](../scripts/test-perception-lab-motion.mjs) ouvre la page via le serveur local, charge le **véritable GLB Mixamo**, vérifie la cadence de marche, capture l'animation d'attaque et confirme les dégâts. WebSuite reste un test visuel générique indépendant des données de jeu. Le moteur de mouvement signale chaque refus au cerveau, qui peut replanifier puis remonter un état bloqué. Le benchmark est indicatif : il ne remplace pas un profilage RTS complet.

Prototype 2D sur plan X/Z avec obstacles simplifiés en disques, sans relief, sans foule multi-agent persistante, sans sauvegarde longue durée. Le champ de vision par défaut est volontairement à 360° pour les premiers tests; l'exploration ne garantit pas de trouver tous les objets cachés. Un LLM très léger pourra plus tard lire snapshot() et produire un ordre structuré, mais n'aura pas à calculer chaque pas.
