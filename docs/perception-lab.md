# WarConquer — Perception Lab

Le [Perception Lab](../perception-lab.html) réutilise l'arène isométrique du [Character Lab](../character-lab.html) : sol, quadrillage, six rochers, lumières, caméra. La scène commune vit dans [arena-scene.js](../scripts/arena-scene.js). Le Character Lab conserve ses contrôles WASD et ses animations.

## Ouverture

Démarrer le serveur existant : node scripts/serve-character-lab.mjs. Ouvrir ensuite http://127.0.0.1:4173/perception-lab.html, ou la version publiée https://www.streamlev.com/WarConquer/perception-lab.html.

Cliquer sur Ennemi, Ressource, Obstacle ou Allié, puis sur le terrain, ajoute un objet. Une fois sélectionné, modifier nom, nature, faction, type de ressource, danger (0–1), caractère bloquant et occultant. Les six rochers sont de vrais obstacles dans ce laboratoire. On peut effacer et recréer la démonstration.

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
| {type:"goto",x:3,z:1} | A* vers la destination |
| {type:"relative",direction:"left",distance:4,id:7} | Orientation relative au début de l'ordre |
| {type:"approach",entityId:"enemy-1",distance:1.2} | Se rapprocher d'une entité connue |
| {type:"find",kind:"resource"} | Chercher dans les souvenirs et explorer l'inconnu adjacent |
| {type:"flee"} | Choisir une position plus sûre |
| {type:"attack",entityId:"enemy-1",distance:1.35} | Approcher puis émettre l'intention attack |
| {type:"collect",entityId:"wood-1",distance:.95} | Approcher puis émettre l'intention collect |

La reconnaissance utilise géométrie, champ de vision, occlusion, mémoire spatiale individuelle et dernière position des objets. Les souvenirs sont plafonnés, et ceux des entités dynamiques expirent. A* planifie **uniquement sur les cellules mémorisées** en pénalisant l'inconnu, tandis que le moteur tranche les collisions réelles. La peur augmente près des ennemis, puis décroît; elle peut déclencher une fuite prioritaire.

## Animations réelles

Le contrôleur du laboratoire charge le GLB depuis le catalogue déjà utilisé par le Character Lab, identifie les groupes d'animation par leur nom et déclenche marche, course pour fuir, attaque et éventuellement ramassage. Une animation de ramassage n'est reconnue que si son clip est explicitement compatible (pickup, pick_up, collect ou gather). Si elle manque, l'action est signalée indisponible et la ressource n'est pas supprimée. Aucune animation d'attaque n'est utilisée comme faux ramassage. Le prototype n'applique encore ni dommages de combat ni économie de ressources.

Si le catalogue ou le modèle 3D ne peut être chargé, le laboratoire utilise clairement un avatar 3D de secours sans prétendre jouer les mouvements Mixamo.

## Vérification et limites

~~~bash
node scripts/test-perception-brain.mjs
~~~

Les tests couvrent le champ de vision, les murs, le brouillard de guerre, A*, la mémoire bornée, les ordres relatifs, la peur, l'attaque/ramassage et 100 cervelets. Le benchmark est indicatif : il ne remplace pas un profilage RTS complet.

Prototype 2D sur plan X/Z avec obstacles simplifiés en disques, sans relief, sans foule multi-agent persistante, sans sauvegarde longue durée. Le champ de vision par défaut est volontairement à 360° pour les premiers tests; l'exploration ne garantit pas de trouver tous les objets cachés. Un LLM très léger pourra plus tard lire snapshot() et produire un ordre structuré, mais n'aura pas à calculer chaque pas.
