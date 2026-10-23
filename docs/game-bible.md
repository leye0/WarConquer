# WarConquer — La Guerre des Jours Effacés
## Bible d'univers et de game design métier — proposition v0.1

> **Statut :** document de conception créative, destiné à la discussion. Les noms, nombres et systèmes ci-dessous sont des propositions cohérentes, pas des décisions définitivement approuvées. Aucun choix d'architecture ou d'implémentation n'est imposé ici.
>
> **Ambition :** retrouver l'immédiateté, le plaisir de construction, les affrontements lisibles et la montée en puissance d'un grand RTS médiéval-fantastique des années 1990, dans un univers original et étonnant pour un public de 2026.

---

## 1. La promesse du jeu

**WarConquer** est un jeu de stratégie en temps réel de conquête médiévale-fantastique. Le joueur commence souvent avec une petite communauté, quelques paysans et un bâtiment central. Il explore, récolte, construit une économie, élève des casernes, recrute archers et guerriers à la hache, fortifie ses frontières, débloque cavalerie, machines de siège, magie et flottes, puis mène des armées contre un adversaire capable d'en faire autant.

**La promesse en une phrase :** *Bâtir un royaume en quelques dizaines de minutes, commander une guerre lisible et spectaculaire, et décider quelle version du passé survivra.*

### Piliers non négociables

1. **RTS classique, pas jeu de cartes ni stratégie au tour par tour.** Sélection d'unités, clics de déplacement et d'attaque, ordres de récolte, construction en temps réel, brouillard de guerre.
2. **Économie compréhensible.** Les paysans restent essentiels du début à la fin. Les ressources sont matérielles, visibles et disputées.
3. **Progression en trois âges.** Un village pauvre devient bourg fortifié, puis puissance militaire et magique. Les évolutions ont des prérequis explicites.
4. **Armées classiques avec une personnalité nouvelle.** Guerriers à la hache, archers, piquiers, cavaliers, prêtres, sorciers, machines de siège, unités volantes et navires.
5. **Deux factions jouables complètes au lancement.** Elles partagent un langage tactique permettant d'apprendre vite, mais possèdent des silhouettes, des motivations, des sorts et quelques avantages distincts.
6. **La bataille décide de la victoire.** L'univers, le récit et les singularités de la carte enrichissent la tactique, sans remplacer l'économie ni la guerre.
7. **Lisibilité avant complexité.** Peu d'effets invisibles, aucune victoire dépendant d'un événement aléatoire irrésistible, aucune obligation de microgérer des dizaines de jauges.
8. **Des parties rejouables.** Campagnes scénarisées, escarmouche contre l'IA et multijoueur, avec règles communes autant que possible.

### Sensations recherchées

- Au début : vulnérabilité, débrouillardise, curiosité face au brouillard.
- Au milieu : frontière mouvante, raids de cavalerie, choix douloureux entre économie et armée.
- À la fin : siège monumental, grandes formations, flotte sur les côtes, magie rare mais décisive.
- Après la partie : « Si j'avais protégé mes paysans / contrôlé ce passage / choisi une autre évolution, j'aurais gagné. »

### Ce que le jeu ne cherche pas à être

Ni simulation politique complexe, ni 4X à l'échelle de siècles, ni jeu de survie artisanale, ni RPG centré sur des héros invincibles. On peut avoir des personnages et des choix narratifs sans diluer la formule RTS.

---

## 2. Le concept narratif : le monde dont l'histoire est falsifiable

### L'accroche

Il y a cent quarante ans, le soleil s'est levé deux fois le même matin.

Au premier lever, le royaume de **Veyr** a gagné une guerre. Au second, cette guerre n'avait jamais eu lieu. Des villes se sont retrouvées bâties sur les ruines de villes qui n'avaient jamais existé ; des enfants se sont souvenus de parents dont aucun registre ne gardait le nom. Au large, une flotte entière a regagné un port qui ne figurait plus sur les cartes.

On a appelé cela **la Première Correction**.

Depuis, les habitants d'**Orvéa** ont appris une vérité terrifiante : le passé n'est pas immuable. Il est maintenu par une antique force appelée **la Trame**, dont les coutures traversent les forêts, les mines, les mers et les champs de bataille. Certains savants savent y imprimer de petites corrections. Les puissants rêvent d'y graver une histoire entière.

À présent, au seuil du **Neuvième Matin**, une nouvelle Correction approche. Une guerre commence pour le contrôle des lieux où l'histoire se noue.

### Le thème contemporain, sans écrans ni science-fiction plaquée

Le cœur de WarConquer parle de **mémoire collective, de vérité fabriquée, de propagande, de patrimoine effacé et du pouvoir de nommer les choses**. Ces préoccupations résonnent avec 2026, mais prennent la forme d'une épopée d'armures, de bois, de pierre, d'encre, de cloches et de sortilèges. Une archive peut être plus dangereuse qu'un dragon ; une villageoise qui se souvient peut faire trembler un empire.

Le récit ne demande pas de croire qu'un camp représente la vérité et l'autre le mensonge : chaque camp protège quelque chose de légitime et commet des violences au nom de cette protection.

### Quatre règles de l'univers

1. **La Trame ne crée rien gratuitement.** Une Correction exige un support physique — une faille, une stèle, un fragment d'Écho — et prélève toujours un prix.
2. **La mémoire résiste.** Certaines personnes, dites les *Dissonantes*, conservent des souvenirs incompatibles avec l'histoire officielle.
3. **On ne ressuscite pas vraiment les morts.** La magie peut convoquer un reflet temporaire ou soigner un vivant, pas restaurer sans conséquence une existence disparue.
4. **Les grandes Corrections sont rarissimes.** Les sorts de bataille sont locaux, temporaires et lisibles. Aucune faction ne rembobine librement une partie.

### Le secret central de la saga

La Trame n'est pas un livre passif : elle conserve *les histoires auxquelles suffisamment de vivants consentent*. Les souverains ont découvert des moyens de simuler ce consentement. Le Neuvième Matin menace de rendre une version officielle de l'histoire permanente — et d'effacer toute personne qui ne peut y être inscrite.

---

## 3. Le monde d'Orvéa

Orvéa est une grande terre fracturée en péninsules et archipels. Les reliefs guident réellement la guerre : cols étroits, grandes forêts exploitables, mines aurifères, gués, falaises, îles, ports et chenaux.

| Région | Identité littéraire | Identité de jeu |
| --- | --- | --- |
| **Veyr-la-Haute** | Capitale des cloches de verre, palais des archivistes, ordre apparent | Plaines, fleuves, grandes villes fortifiables |
| **Les Marches Rouges** | Villages rayés des cartes, drapeaux rapiécés, autels de souvenirs | Forêts, embuscades, chemins étroits |
| **Les Dents d'Ambre** | Montagnes striées de filons d'or et de fossiles impossibles | Mines riches, cols à défendre |
| **L'Archipel des Veilles** | Ports submergés de brouillard, îlots de sel et épaves de plusieurs époques | Batailles navales, traversées, ressources rares |
| **La Plaine Blanche** | Région où des journées entières ont disparu | Grand champ de bataille et sites neutres |
| **Le Cœur Cousu** | Cicatrice centrale où deux passés coexistent par endroits | Derniers scénarios, positions stratégiques singulières |

**Paysage vivant :** une route pavée peut disparaître sous un champ de fleurs près d'une Couture ; une tour en ruine peut projeter l'ombre d'une tour intacte. Ces bizarreries sont d'abord une esthétique et des objectifs de mission. Elles ne rendent jamais imprévisible le déplacement des unités dans les règles standard.

### Population et quotidien

Les peuples d'Orvéa ne sont pas divisés sommairement en « bons humains » et « méchants monstres ». On y trouve des humains, des lignées à la peau minérale, des porteurs de masques hérités et des créatures nées de souvenirs collectifs. Chaque faction est une coalition sociale, avec fermiers, marins, soldats, artisans, desservants, commerçants et familles. Les paysans ne sont pas des pions anonymes dans l'histoire : le contrôle de la nourriture et le sort des villages sont les raisons concrètes de la guerre.

---

## 4. Les factions jouables

### A. La Couronne de Verre

**Devise :** « Qu'une seule histoire demeure, afin que tous puissent vivre dedans. »

Coalition de cités, de guildes et de maisons militaires qui maintiennent les archives officielles. La Couronne prétend empêcher que le monde ne se défasse. Elle nourrit les villes, entretient des routes sûres et abrite les populations contre les Corrections sauvages. Mais ses archivistes effacent les faits qui menacent la stabilité — parfois jusqu'à effacer des communautés de l'histoire.

- **Silhouette :** manteaux bleu nuit, ivoire, bronze poli, bannières fendues, casques à visière de verre fumé.
- **Architecture :** charpentes géométriques, pierre blonde, hautes tours d'observation, vitraux opaques, cloches.
- **Musique :** chœurs retenus, tambours militaires, cordes graves, verre chantant.
- **Personnalité tactique :** défense structurée, archers précis, formations solides, magie de protection et de contrôle.
- **Faiblesse intentionnelle :** moins de mobilité tactique et moins de tromperie que sa rivale.
- **Ambiguïté morale :** la sécurité est réelle ; la censure l'est aussi.

**Figures importantes :**
- **Régente Yselle d'Ambre**, convaincue que la liberté de réécrire l'histoire provoquerait une catastrophe.
- **Archiviste Oren Vale**, jeune enquêteur qui découvre des incohérences dans les victoires de sa propre nation.
- **Capitaine Maël Voss**, commandant honorable ayant participé à la disparition d'un village sans se souvenir de l'ordre.

### B. Les Marches Délivrées

**Devise :** « Nous étions là, même si vos livres nous nient. »

Confédération de villages bannis, de caravanes, de lignages Dissonants et de communautés rescapées d'anciennes Corrections. Ses habitants portent les noms de leurs morts cousus dans leurs vêtements. Les Marches veulent ouvrir la Trame pour rétablir les vies et les terres qu'on leur a confisquées. Elles n'ont pas toutes la même idée de ce qui doit revenir.

- **Silhouette :** rouge oxyde, noir de charbon, cuivre terni, capuches cousues, masques en bois, fils flottants.
- **Architecture :** maisons autour d'arbres conservés, toits de roseaux noirs, bois renforcé, clochers tordus, stèles couvertes de tissu.
- **Musique :** percussions sèches, voix solo, cordes frottées, chants polyphoniques désaccordés.
- **Personnalité tactique :** raids, mobilité, éclaireurs, embuscades, magie d'illusion et de perturbation.
- **Faiblesse intentionnelle :** positions fortifiées légèrement moins résistantes, armée plus exigeante à protéger.
- **Ambiguïté morale :** leur quête de réparation peut sacrifier les personnes qui vivent dans le présent.

**Figures importantes :**
- **Nara des Sept-Noms**, stratège ayant des souvenirs de sept enfances incompatibles.
- **Bram Fendracine**, ancien bûcheron devenu chef des compagnies de hache.
- **La Ravaudeuse Sève**, mystique capable de faire parler les vestiges d'une maison effacée.

### La troisième force : les Huissiers du Minuit

Non jouables dans la version de base. Ce sont des gardiens de la Trame, vêtus de plaques gravées et accompagnés de bêtes pâles. Ils n'attaquent pas « par méchanceté » : ils retirent ce qui n'appartient plus à l'histoire en vigueur. Leur véritable allégeance se révèle progressivement. Ils apparaissent comme ennemis neutres, gardiens de sites ou menace de campagne ; ils n'interrompent pas arbitrairement les escarmouches standard.

---

## 5. Une partie type

Une partie de conquête dure **environ 20 à 40 minutes** à titre d'objectif de rythme, avec des formats plus courts possibles.

1. **Naissance du camp (âge I).** Un centre, quatre paysans, des ressources proches, la carte cachée. Construire maisons et caserne, récolter, entraîner les premiers combattants.
2. **Premières frontières.** Éclaireurs, archers, guerriers à la hache, raids contre travailleurs isolés, tours aux goulets.
3. **Le bourg (âge II).** Forge, cavalerie, machines de siège, sanctuaire, ports sur les cartes maritimes, accès à l'Écho.
4. **La citadelle (âge III).** Unités d'élite, sorts puissants, aviation fantastique, grands sièges et contrôle des derniers gisements.
5. **Dénouement.** Victoire militaire, défaite, reddition ou objectif narratif propre à une mission.

### Contrat d'interaction

- Cliquer sélectionne ; glisser forme un groupe ; clic droit donne l'ordre contextuel.
- Ordres attendus : se déplacer, attaquer, attaquer en mouvement, défendre une position, patrouiller, récolter, construire, réparer, embarquer, débarquer, lancer un sort.
- Groupes d'unités et points de ralliement, files de recrutement visibles, production interrompue si les ressources ne sont pas disponibles au lancement.
- Les paysans sont sélectionnables comme des unités ordinaires ; un travailleur n'effectue qu'une tâche à la fois.
- Les bâtiments appartiennent physiquement au terrain et bloquent la circulation.
- Les morts et bâtiments détruits sont définitifs pendant la partie, sauf scénarios narratifs explicitement spéciaux.

### La guerre doit se lire

Un joueur doit comprendre *pourquoi* il a perdu un échange : portée des archers, charge de cavalerie, muraille, résistance des piquiers, efficacité du siège, contre-sort. Les effets ont des sons et silhouettes reconnaissables ; les caractéristiques essentielles restent consultables.

---

## 6. Économie, population et exploration

### Trois ressources

| Ressource | Fiction | Obtention | Usage |
| --- | --- | --- | --- |
| **Or** | Monnaie des cités et métal de guerre | Paysans dans les mines ; retour au centre ou dépôt | Paysans, soldats, bâtiments, recherches |
| **Bois** | Charpentes, flèches, palissades et navires | Paysans coupant des arbres ; retour à un dépôt | Construction, archers, siège, flotte |
| **Écho** | Sel cristallisé autour des Coutures, capable de retenir une version du réel | Extraction à partir de l'âge II dans des filons terrestres ou récifs marins | Magie supérieure, unités avancées, améliorations de fin de partie |

**Règle capitale :** seules l'or et le bois sont nécessaires pour construire l'économie initiale et les premières troupes. L'Écho donne des raisons de se disputer le territoire au milieu et à la fin de la partie ; il ne verrouille jamais une ouverture de jeu ordinaire.

- Les gisements ont une quantité finie ; les arbres sont abattus et modifient progressivement les passages.
- Les paysans transportent une charge puis doivent la déposer. Ils peuvent mourir avec leur charge.
- Les mines et filons sont des objets de carte, pas une ressource créée à partir de rien.
- Un **Puits d'Écho** contrôle un filon terrestre ; un navire spécialisé récolte sur les récifs. Les cartes sans littoral fournissent de l'Écho terrestre.
- Chaque joueur voit son stock courant et son approvisionnement en population.

### Population et logements

Le centre donne **10 places**, chaque maison **6 places**, et le plafond de référence est **120**. Le recrutement est impossible si le coût en population dépasse les places disponibles. Une maison détruite peut placer un joueur au-dessus de son plafond : ses unités existantes ne disparaissent pas, mais il ne peut plus en recruter tant que la situation n'est pas rétablie.

Proposition de coût en population : paysan, hache, archer et pique **1** ; garde lourd et cavalier **2** ; soutien et mage **2** ; engin de siège **3** ; volant **4** ; navires **2 à 5** selon leur classe.

### Brouillard de guerre

- Les endroits jamais visités sont noirs.
- Le terrain découvert demeure connu, mais les unités adverses ne sont visibles que dans les champs de vision actuels.
- Une armée cachée dans une forêt n'est pas automatiquement invisible ; la forêt gêne la vision et favorise la surprise dans certains terrains balisés.
- Les tours, éclaireurs, unités volantes et sorts de révélation augmentent la reconnaissance.
- Aucun joueur ne connaît sans exploration les positions ennemies, les ressources lointaines ou les emplacements des sites narratifs.

### Ressources neutres et commerce

Pas de marché permettant d'acheter infiniment les trois ressources. Les ports et relais peuvent proposer dans certaines missions des échanges limités, indiqués à l'avance. En escarmouche standard, l'économie reste fondée sur l'extraction et le contrôle du terrain.

---

## 7. Âges et arbre de progression

Les deux civilisations suivent la même structure économique pour préserver une courbe d'apprentissage commune. Les noms et visuels diffèrent.

| Palier | Couronne de Verre | Marches Délivrées | Fonction |
| --- | --- | --- | --- |
| **I — Campement** | Maison du Sceau | Foyer des Noms | Paysans, maisons, caserne, exploitation de base, armée légère |
| **II — Bourg** | Halle des Registres | Halle des Braises | Forge, cavalerie, siège, sanctuaire, port, Écho |
| **III — Citadelle** | Palais des Veilles | Cœur des Marches | Magie avancée, unités aériennes, améliorations et artillerie lourde |

### Passage I → II

Exige une caserne et une scierie opérationnelles, puis un investissement en or et bois. L'amélioration du centre prend du temps, annoncé à l'écran. Elle ne retire pas les unités déjà disponibles.

### Passage II → III

Exige une forge et un sanctuaire, ainsi qu'une quantité d'Écho. Les bâtiments débloqués à l'âge III nécessitent encore leurs propres coûts et temps de construction.

### Principes de progression

- Une recherche est acquise **pour la partie en cours** et s'applique aux unités concernées déjà produites, sauf exception explicitement décrite.
- Détruire un bâtiment n'efface pas une recherche terminée. En revanche, il faut posséder un bâtiment de production valide pour créer de nouvelles unités.
- Les améliorations ont en général trois niveaux lisibles : armes, armures, portée/précision, efficacité de récolte, vitesse des navires.
- On peut contourner tactiquement une partie de l'arbre (par exemple jouer infanterie + siège sans cavalerie) ; aucune voie unique n'est obligatoire.
- Pas de « prestige » ni de progression permanente qui déséquilibrerait les parties multijoueurs.

---

## 8. Bâtiments : catalogue métier

Les noms ci-dessous sont les appellations de la Couronne / des Marches. Les fonctions sont identiques, sauf spécialisation indiquée.

| Bâtiment | Âge | Fonction principale et évolution |
| --- | --- | --- |
| **Maison du Sceau / Foyer des Noms** | I | Centre initial : forme les paysans, reçoit l'or, fait progresser l'âge ; devient Halle puis Palais/Cœur |
| **Maison de pierre / Maison des Veillées** | I | Fournit des places de population ; modèle visuel amélioré aux âges supérieurs sans micromanagement |
| **Caserne / Cercle des Haches** | I | Produit combattants de hache et piquiers, puis infanterie lourde au II |
| **Scierie / Atelier de Racines** | I | Reçoit le bois, améliore rendement des bûcherons et traits des archers ; prérequis du II |
| **Champ de tir / Butte des Flèches** | I | Produit les archers et leurs recherches spécialisées |
| **Dépôt / Grenier de route** | I | Point de retour des matières à proximité des sites d'exploitation |
| **Tour de guet / Vigie cousue** | I | Détecte, observe ; peut évoluer en tour de flèches au II ou tour runique au III |
| **Forge du Sceau / Forge des Cendres** | II | Améliore armes et armures ; prérequis du III |
| **Écurie / Cour des Montures** | II | Produit les cavaliers ; permet la recherche de charge |
| **Atelier de siège / Atelier des Brisures** | II | Produit béliers et lance-pierres ; améliore les projectiles |
| **Sanctuaire / Maison des Ravaudeuses** | II | Produit unités de soutien ; débloque magie et constitue un prérequis du III |
| **Puits d'Écho / Puits de Souvenir** | II | Extraction d'Écho sur filon, exploité par des paysans assignés |
| **Port militaire / Grève des Barques** | II | Produit navires de transport et de guerre, récolteurs marins là où la carte le permet |
| **Observatoire / Cercle des Possibles** | III | Produit les mages et leurs sorts avancés |
| **Aire des Vigiles / Nid des Murmures** | III | Produit les unités volantes et leurs améliorations |
| **Remparts et portes** | II | Fortifications destructibles et réparables ; ouvertures explicites pour les unités alliées |

**Règle de construction :** seul le paysan construit et répare. Les bâtiments exigent un sol constructible, peuvent être endommagés et doivent être accessibles aux unités qu'ils produisent. Un chantier inachevé peut être attaqué. Pas de placement directement sur une unité ennemie ou un obstacle.

**Évolutions visuelles :** à chaque âge, l'identité de la colonie se renforce — plus de pierre, de vitraux et de cloches pour la Couronne ; plus de charpentes vivantes, de drapeaux et de fils de mémoire pour les Marches. La progression doit se voir de loin.

### Un exemple de village qui grandit

**Campement :** centre, quatre maisons, scierie, caserne et tour de guet.

**Bourg :** centre élevé, forge, champs de tir, écurie, atelier de siège, sanctuaire, deuxième dépôt près d'une mine distante.

**Citadelle :** remparts et tours évoluées, observatoire, aire volante, lignes de production multiples, ports et garnisons aux points stratégiques.

---

## 9. Unités terrestres : toutes les fonctions classiques

Chaque faction a un équivalent pour les grandes fonctions. Les archétypes sont volontairement familiers ; leur existence ne suppose pas de reprendre des personnages, noms propres, graphismes ou voix d'une autre licence.

| Rôle et âge | Couronne de Verre | Marches Délivrées | Ce que l'unité apporte |
| --- | --- | --- | --- |
| **Travailleur — I** | Paysan du Sceau | Paysan des Veillées | Récolte, construit, répare ; peut se défendre très faiblement |
| **Hache légère — I** | Homme de hache | Fendeur de racines | Premier vrai soldat ; efficace au contact contre cibles légères |
| **Anti-cavalerie — I** | Piquier de garnison | Porte-épieu | Maintient une ligne, punit les charges, moins bon face aux archers |
| **Archer — I** | Archer des Veilles | Archer aux fils rouges | Attaque à distance, excellent derrière des troupes de contact, fragile seul |
| **Infanterie lourde — II** | Garde du Sceau | Porte-muraille | Encaisse, protège archers et engins, coûte plus cher |
| **Cavalerie — II** | Chevalier des Cloches | Cavalier des Cerfs-brasiers | Attaque rapide, raid contre archers et paysans, vulnérable aux piquiers |
| **Siège — II** | Lance-pierres de bronze | Catapulte des Vestiges | Détruit les bâtiments à distance, lente et vulnérable au contact |
| **Bélier — II** | Bélier du Palais | Bélier-racine | Ouvre les portes et remparts ; courte portée, forte résistance |
| **Soutien — II** | Chapelain des Preuves | Ravaudeuse | Soigne et améliore temporairement les alliés ; faible en combat direct |
| **Mage — III** | Archiviste de guerre | Tisseur des Possibles | Sorts coûteux qui modifient localement un affrontement |
| **Volant — III** | Vigile de verre | Grand Miroir-de-nuit | Traverse obstacles, reconnaît, harcèle ; coûteux, contré par projectiles et sorts |

### Quelques touches distinctives

- **Homme de hache (Couronne) :** peut apprendre *Garde serrée*, petite réduction des dégâts reçus en restant près d'autres fantassins.
- **Fendeur de racines (Marches) :** peut apprendre *Élan de friche*, courte accélération après avoir détruit un obstacle ou vaincu un ennemi au contact.
- **Archer des Veilles :** amélioration de précision/portée légèrement supérieure à un coût plus élevé.
- **Archer aux fils rouges :** peut apprendre un déplacement bref plus rapide, au prix d'une portée un peu inférieure.
- **Chevalier des Cloches :** charge frontale disciplinée.
- **Cavalier des Cerfs-brasiers :** meilleur contournement, résistance inférieure.
- **Vigile de verre :** observateur aérien et harceleur de cibles isolées.
- **Grand Miroir-de-nuit :** créature faite de plumes et de souvenirs dissonants, sensible aux effets anti-magie.

**Principe d'équilibrage :** une différence de faction ne doit pas supprimer le rôle d'une famille d'unités. On peut jouer de manière crédible archers + piquiers ou infanterie + siège dans les deux camps.

### Relations de contre

| Menace ennemie | Réponse naturelle | Risque de la réponse |
| --- | --- | --- |
| Archers en masse | Cavalerie, siège léger ou attaque de flanc | Piquiers qui protègent les archers |
| Cavalerie | Piquiers, terrain étroit et fortifications | Archers derrière la cavalerie |
| Infanterie lourde | Magie de zone, archers améliorés, manœuvre | Attaque rapide sur les unités fragiles |
| Tours et remparts | Béliers et lance-pierres | Sortie de cavalerie, raid de flanc |
| Mages | Éclaireurs, cavalerie rapide, silence magique | Ligne d'infanterie qui les protège |
| Unités volantes | Archers améliorés, tours anti-aériennes, sort spécialisé | Artillerie ou diversion au sol |
| Armée groupée | Sorts de zone et siège | Dispersion et attaque sur plusieurs fronts |

Il n'y a pas de réussite critique aléatoire majeure par défaut. La portée, les dégâts, l'armure, la vitesse et le type de cible donnent des résultats prévisibles.

---

## 10. Mer, débarquements et ciel

La mer n'est pas décorative : les campagnes côtières et certaines cartes d'escarmouche comportent des routes navales stratégiques.

| Classe | Couronne | Marches | Fonction |
| --- | --- | --- | --- |
| **Transport — II** | Nef de passage | Barge cousue | Embarque une petite force terrestre, non adaptée au duel naval |
| **Guerre légère — II** | Patrouilleur de verre | Brise-écume | Combat et escorte les transports |
| **Récolte d'Écho — II** | Dragueur de sel | Chaloupe des Brumes | Exploite les récifs et rapporte l'Écho au port |
| **Artillerie lourde — III** | Galéasse du Sceau | Arche de Cendre | Longue portée contre navires et fortifications côtières |

- Un navire ne traverse pas la terre ; les transports exigent un rivage praticable pour débarquer.
- Les unités terrestres ordinaires ne marchent pas sur l'eau.
- Les bâtiments côtiers peuvent être attaqués depuis la mer lorsque leur portée le permet.
- Un débarquement ne doit pas placer automatiquement des troupes sur une case bloquée.
- La flotte a son propre rapport de forces : escorte légère contre transport, artillerie contre fortification, attaque de proximité contre artillerie isolée.
- Les cartes purement terrestres restent complètes et équilibrables sans port ni navire.
- Les volants ignorent reliefs et eaux mais ne transportent pas d'armée dans la version initiale.

---

## 11. Magie : agir sur les preuves plutôt que lancer de simples projectiles colorés

La magie est fondée sur les *preuves*, les *souvenirs* et les *possibles*. Son habillage est singulier ; sa logique tactique reste claire.

**Deux couches séparées :**
- **Écho** : ressource économique pour former certains spécialistes, construire les bâtiments arcaniques et rechercher des sorts.
- **Mana** : réserve individuelle des chapelains, ravaudeuses et mages ; elle se régénère avec le temps, sans coût d'Écho à chaque lancement dans les règles standard.

Pas de recherche qui entraîne la victoire sans possibilité de contre. Les sorts ont portée, coût en mana, durée et effet affichés.

### Couronne de Verre : la magie du Sceau

| Sort | Lanceur | Effet tactique proposé |
| --- | --- | --- |
| **Preuve vivante** | Chapelain | Soigne une unité alliée vivante ; n'a aucun effet sur un mort |
| **Contresceau** | Chapelain | Bouclier temporaire sur une petite cible ou unité de siège |
| **Ligne de preuve** | Archiviste | Dévoile brièvement une zone cachée et les illusions qu'elle contient |
| **Décret de silence** | Archiviste | Empêche pendant quelques secondes un petit groupe d'ennemis de lancer des sorts |
| **Ancrage** | Archiviste | Ralentit des adversaires dans une petite zone ; ne les immobilise pas indéfiniment |
| **Heure scellée** | Archiviste, recherche finale | Réduit brièvement les dégâts subis par des alliés dans un périmètre visible ; très coûteux en mana |

### Marches Délivrées : la magie de la Ravaudure

| Sort | Lanceur | Effet tactique proposé |
| --- | --- | --- |
| **Fil de vie** | Ravaudeuse | Soin progressif d'un allié ; interrompu s'il meurt |
| **Nœud de courage** | Ravaudeuse | Petit bonus temporaire de déplacement et de résistance |
| **Faux souvenir** | Tisseur | Crée une ou deux silhouettes illusoires ; elles ne blessent pas et se dissipent sous les coups |
| **Fêlure** | Tisseur | Fragilise momentanément l'armure d'une unité ou d'un bâtiment |
| **Voie des absents** | Tisseur | Accélère un groupe pendant quelques secondes, utile pour raid ou retraite |
| **Le Monde aurait pu** | Tisseur, recherche finale | Crée pendant quelques secondes une zone de silhouettes trompeuses, sans dégâts directs ; les unités réelles restent ciblables et les illusions révélables |

### Règles communes des sorts

1. Une unité sous silence ne lance pas de sorts ; elle peut continuer à se déplacer et attaquer si son profil le permet.
2. Les illusions n'occupent pas de place de population permanente, ne récoltent rien, ne construisent rien et ne capturent pas de site.
3. Les soins ne dépassent pas les points de vie maximum.
4. Aucun contrôle mental permanent, aucune destruction globale de base à un clic et aucun retour intégral en arrière.
5. Chaque sort important possède au moins une réponse : dispersion, éclaireur, silence, attente, retrait, anti-magie ou attaque du lanceur.
6. Les effets les plus spectaculaires sont rares, courts et signalés au joueur adverse.

---

## 12. Fortifications, neutralité et Coutures

### Défense

Les tours tirent sur les ennemis visibles dans leur portée. Elles nécessitent une garnison ou un entretien ? **Non dans la version initiale** : une fois construites, elles fonctionnent automatiquement. Les tours avancées peuvent choisir une spécialisation anti-sol ou anti-air. Les murs et portes ralentissent une armée mais ne rendent jamais une base invulnérable.

### Sites neutres : les Relais de Mémoire

Certaines cartes possèdent un ou deux **Relais de Mémoire**, anciens sanctuaires disputés. Un paysan peut les revendiquer en restant quelques secondes à proximité sans opposition ennemie.

- Contrôler un Relais offre un petit revenu régulier d'Écho et un champ de vision local.
- Un relais n'engendre pas d'armée, ne permet pas de téléportation gratuite et peut changer de main.
- Il est absent des cartes débutantes et facultatif dans le mode d'escarmouche classique.
- Il crée une raison d'affronter l'adversaire hors de sa base sans devenir une seconde condition de victoire obligatoire.

### Les Coutures : étrangeté narrative, équité mécanique

Une Couture est un endroit où des versions différentes du passé affleurent. Dans une campagne, elle peut être un objectif (« garder la stèle pendant six minutes »), une révélation visuelle ou un environnement scénarisé. Dans une escarmouche standard, elle ne réarrange jamais secrètement la carte, ne déplace jamais un bâtiment et ne tue pas au hasard une armée.

**Variante ultérieure facultative :** événements de Correction annoncés à l'avance, avec zones marquées et effets symétriques. Cette variante ne fait pas partie des règles compétitives de base.

---

## 13. Règles de partie et conditions de victoire

### Escarmouche : Conquête

- **Départ standard :** un centre de niveau I, quatre paysans, un petit stock d'or et de bois, positions de départ éloignées, ressources de proximité comparables.
- **Joueurs :** 1 contre 1 en priorité ; 2 contre 2 et chacun pour soi prévus dans la définition du produit.
- **Diplomatie :** alliances fixées au début en mode équipe, sans trahison diplomatique en cours de partie dans la version initiale.
- **Visibilité :** brouillard de guerre activé.
- **Production :** unités formées dans des bâtiments ; pas d'apparition gratuite périodique de soldats.
- **Défaite :** un joueur est éliminé lorsqu'il ne possède plus aucune unité ni aucun bâtiment. Pour empêcher la recherche interminable d'un dernier paysan, les positions des actifs restants deviennent visibles pour tous lorsque le joueur ne possède plus aucun centre, aucune structure de production et moins de trois unités.
- **Victoire :** dernier joueur ou dernière équipe non éliminée ; la reddition est possible.
- **Pas de limite de temps obligatoire** dans le mode classique.
- **Pas d'attaque amicale automatique** de zone pour les archers et catapultes dans la règle initiale ; les effets magiques explicitent s'ils touchent des alliés.

### Campagne : objectifs variés

- Détruire un bastion.
- Protéger une caravane ou une flotte.
- Tenir un col pendant un temps annoncé.
- Libérer des paysans ou ramener un personnage vivant au centre.
- Capturer puis défendre des Relais.
- Saboter un chantier ou un port.
- S'échapper avec un contingent limité.
- Remporter une bataille décisive avec construction complète de base.

Les missions spéciales indiquent clairement si le joueur peut construire, exploiter des mines, remplacer ses troupes et perdre un personnage important.

### Difficulté et équité

L'IA peut prendre de meilleures décisions, explorer plus activement et choisir des attaques plus élaborées. Elle ne doit pas recevoir des ressources secrètes ou une vision omnisciente en difficulté normale. Les modes de difficulté avancée peuvent proposer explicitement un handicap économique, identifié comme tel.

---

## 14. Économie chiffrée indicative pour une première discussion

Les valeurs servent uniquement à visualiser les proportions. Elles **ne sont pas équilibrées par test** et ne doivent pas devenir des constantes de production sans validation.

**Notation :** O = or, B = bois, É = Écho.

| Élément | Coût initial indicatif | Notes |
| --- | --- | --- |
| Paysan | 50 O | 1 population |
| Homme de hache / Fendeur | 75 O + 10 B | 1 population |
| Piquier | 100 O + 20 B | 1 population |
| Archer | 90 O + 30 B | 1 population |
| Infanterie lourde | 125 O + 20 B | 2 populations |
| Cavalier | 220 O + 40 B | 2 populations |
| Lance-pierres | 260 O + 180 B | 3 populations |
| Bélier | 210 O + 160 B | 3 populations |
| Chapelain / Ravaudeuse | 170 O + 20 B + 35 É | 2 populations |
| Archiviste / Tisseur | 230 O + 40 B + 70 É | 2 populations |
| Volant | 350 O + 60 B + 110 É | 4 populations |
| Maison | 65 O + 90 B | +6 populations |
| Caserne | 180 O + 140 B | Âge I |
| Scierie | 130 O + 110 B | Âge I |
| Champ de tir | 190 O + 150 B | Âge I |
| Forge | 230 O + 160 B | Âge II |
| Écurie | 260 O + 200 B | Âge II |
| Atelier de siège | 260 O + 220 B | Âge II |
| Sanctuaire | 240 O + 150 B + 40 É | Âge II |
| Passage au bourg | 500 O + 280 B | Caserne + scierie requises |
| Passage à la citadelle | 650 O + 400 B + 100 É | Forge + sanctuaire requis |

**Cibles d'équilibrage à vérifier plus tard :** plusieurs ouvertures viables, premier contact précoce possible, passage au II significatif, siège contrable avant l'âge III, magie spectaculaire mais non dominante, économie préservant l'intérêt des paysans pendant toute la partie.

---

## 15. Campagnes : deux vérités d'une même guerre

Chaque faction possède **10 missions** découpées en trois actes. Elles traversent la même chronologie, parfois depuis des fronts opposés. Les histoires ne sont pas de simples copies inversées : elles révèlent des mensonges différents.

### Acte I — Les cartes qui mentent

La Couronne réprime une insurrection qu'elle croit manipulée. Les Marches défendent des villages qui ont disparu des registres — et, bientôt, des souvenirs des voisins.

| Mission Couronne | Proposition d'objectif et de récit |
| --- | --- |
| **C1. Le blé des absents** | Construire une petite base, protéger une récolte, repousser des fendeurs. Première leçon : les travailleurs font tenir le royaume. |
| **C2. La route de l'encre** | Escorter les archives d'une ville à l'autre ; apprendre reconnaissance, archers et piquiers. |
| **C3. Les cendres de Val-Muet** | Prendre un village insurgé ; découvrir qu'aucune preuve ne confirme l'ordre reçu. |
| **C4. La cloche fendue** | Tenir une forteresse contre plusieurs attaques, puis contre-attaquer avec la première force de siège. |

| Mission Marches | Proposition d'objectif et de récit |
| --- | --- |
| **M1. Le village qui n'existe pas** | Sauver des paysans, établir un foyer, refouler des soldats de la Couronne. |
| **M2. Les noms dans la forêt** | Exploration, haches et archers ; découvrir des cartes contradictoires. |
| **M3. Du sel dans les plaies** | Capturer un premier Relais de Mémoire et empêcher son effacement. |
| **M4. La bannière rapiécée** | Unifier trois communautés, défendre un col et apprendre les machines de siège. |

### Acte II — Les guerres empruntées

Les deux armées cherchent de l'Écho, traversent l'archipel et découvrent qu'une troisième force guide les Corrections.

| Mission Couronne | Proposition d'objectif et de récit |
| --- | --- |
| **C5. L'impôt des îles** | Développer un port, escorter un récolteur d'Écho et tenir une route navale. |
| **C6. Les témoins impossibles** | Protéger Oren et son enquête ; apparition des premiers sorts et des Huissiers. |
| **C7. Les murs de la version juste** | Assiéger une ville fortifiée sans détruire une archive que la Régente veut récupérer. |

| Mission Marches | Proposition d'objectif et de récit |
| --- | --- |
| **M5. Les barques du retour** | Débarquer sur une île et reprendre un port d'où partirent jadis les exilés. |
| **M6. Sept vies pour Nara** | Défendre une mystique en quête de ses souvenirs ; débloquer la Ravaudure avancée. |
| **M7. Les pierres qui se souviennent** | Prendre des mines et des sites d'Écho avant les Huissiers ; grands affrontements économiques. |

### Acte III — Le Neuvième Matin

La Couronne apprend que son ordre dépend d'un mensonge fondateur. Les Marches découvrent que rendre tous les passés simultanément réels ferait disparaître les vivants d'aujourd'hui.

| Mission Couronne | Proposition d'objectif et de récit |
| --- | --- |
| **C8. Le procès des morts** | Choisir de sauver des civils ou de sécuriser plus vite des fortifications ; choix narratif et mission militaire complets. |
| **C9. La dernière copie** | Combat terrestre et naval pour défendre un fragment de la Trame ; trahison d'une partie de la Couronne. |
| **C10. Le Neuvième Matin** | Assaut final sur le Cœur Cousu. Yselle et Oren doivent choisir ce qui sera conservé plutôt que censuré. |

| Mission Marches | Proposition d'objectif et de récit |
| --- | --- |
| **M8. Les visages de demain** | Rencontrer des personnes dont les familles n'existeraient pas dans le passé restauré. |
| **M9. La guerre des sept souvenirs** | Affronter une faction radicale des Marches et les Huissiers ; siège à plusieurs fronts. |
| **M10. Ceux qui restent** | Percée vers le Cœur Cousu ; décider si la libération vaut une nouvelle disparition de masse. |

### La fin proposée : le Serment des Vivants

Les deux versions de la campagne convergent sur un principe : aucun pouvoir ne devrait posséder seul la Trame. L'histoire ne peut pas devenir parfaitement objective par décret, mais les vivants peuvent refuser qu'elle soit scellée contre eux. Les derniers choix modifient les épilogues, les personnages qui survivent et certaines scènes ; ils ne changent pas secrètement les règles du multijoueur.

**Révélation finale :** les Huissiers n'étaient pas les maîtres de la Trame. Ils étaient les serviteurs de la première grande falsification, chargés de maintenir un monde qui aurait dû se souvenir d'autre chose.

---

## 16. Personnages, villages et narration pendant la partie

La campagne raconte son histoire avec :
- des introductions brèves illustrées comme des manuscrits contradictoires ;
- de courts dialogues au début et pendant les missions ;
- des réactions lorsqu'un village, une archive ou un personnage important est perdu ;
- des messages succincts après un objectif ;
- des épilogues qui montrent les conséquences humaines de la victoire.

Les personnages importants ne deviennent pas des super-soldats obligatoires en escarmouche. Une mission peut leur donner une présence spéciale, mais l'essentiel de la puissance du joueur vient de l'économie et de l'armée.

### Extrait d'ouverture — ton de référence

> Le huitième jour de l'automne, la ville de Mereval fut brûlée.
>
> Le neuvième, ses habitants revinrent.
>
> Le dixième, on déclara qu'il n'y avait jamais eu de ville à cet endroit.
>
> Dans les champs, pourtant, les paysans heurtaient encore des fondations avec leurs bêches. On les obligea à les déterrer, puis on leur ordonna de jurer que les pierres n'avaient jamais été là.
>
> C'est ainsi que commença la guerre : non par la mort d'un roi, mais parce qu'une femme refusa de mentir sur une pierre.

### Extrait de dialogue — une décision sans bons ni méchants

**Oren :** « Si vous ouvrez les Registres, des centaines de milliers d'enfants perdront le monde où ils sont nés. »

**Nara :** « Et si vous les fermez, combien de nos enfants faudra-t-il encore prétendre n'avoir jamais vus ? »

**Oren :** « Je ne sais plus quelle histoire est vraie. »

**Nara :** « Alors commencez par regarder qui souffre quand vous en choisissez une. »

---

## 17. Direction artistique et sonore

**Mot d'ordre :** *fantasy médiévale, étrange et tactile ; la beauté d'un vitrail fêlé sur un champ de bataille boueux.*

- **Graphismes :** villages chaleureux au milieu d'un monde inquiétant, silhouettes immédiatement distinctes, bâtiments lisibles à petite échelle. Le fantastique naît de détails impossibles : ombres en retard, lettres qui tombent d'une stèle, rubans noués à des branches qui n'existent plus.
- **Deux palettes identifiables :** Couronne bleu nuit/ivoire/or ; Marches rouge oxyde/noir/cuivre. Les couleurs de joueur restent distinctes des couleurs de faction.
- **Animations :** gestes clairs de récolte, bois qui tombe, marteaux sur chantier, flèches perceptibles, cavalier qui charge, impact fort du siège.
- **Magie :** moins de boules de feu génériques ; plutôt fissures de calligraphie lumineuse, empreintes de pas qui persistent, vitraux flottants, fils rouges tirés dans l'air. Les zones d'effet doivent être lisibles.
- **Interface :** pierre, encre et laiton simplifiés ; jamais au détriment de la lisibilité des commandes.
- **Son :** chaque unité acquiesce avec sa personnalité, les attaques sont distinctes, l'annonce d'une tour assiégée ou d'une mine épuisée est immédiatement identifiable.
- **Musique :** thèmes nobles qui se désaccordent subtilement, mêlant folklore, chœurs, percussion martiale et textures étranges. Ne jamais sacrifier la perception des événements du combat.

### Les sensations « 2026 »

La modernité vient de la direction artistique assumée, du récit à double lecture et du confort de jeu : commandes réactives, lisibilité, accessibilité, parties reprises/observables selon modes. Pas d'obligation d'ajouter de la science-fiction, du jargon technologique, des NFT, des saisons payantes ou des mécaniques de rétention.

---

## 18. Modes de jeu et promesse produit

### Campagne solo

Deux récits complets, des tutoriels intégrés aux premières missions, des sauvegardes de progression et une difficulté sélectionnable. Les dix missions de chaque faction ne sont pas toutes de simples « détruire l'ennemi ».

### Escarmouche

Choix de faction, carte, alliés, adversaires IA, conditions de départ et vitesse de partie. Les cartes standards doivent permettre au moins deux stratégies crédibles et plusieurs chemins d'attaque.

### Multijoueur

1 contre 1 en priorité ; 2 contre 2 et chacun pour soi en extension logique du mode. Règles symétriques, brouillard de guerre commun, aucune unité vendue ou avantage de puissance réservé à un acheteur. La version standard exclut les événements de Correction aléatoires.

### Modes particuliers facultatifs, après validation du cœur

- **Siège royal :** l'assaillant dispose de ressources supplémentaires, le défenseur de murs avancés.
- **Les Trois Relais :** victoire possible en tenant les trois sites assez longtemps ; règles annoncées.
- **Matin instable :** variantes de Coutures prévisibles et télégraphiées pour partie amicale.

Ces modes ne sont pas des dépendances de la première version jouable.

---

## 19. Ce que « presque Warcraft II » signifie et ce qui doit rester original

**À préserver dans le comportement général :**
- vue stratégique avec nombreux ordres directs ;
- travailleurs et collecte de ressources ;
- construction de bases et logements ;
- casernes, archers, hommes de hache, cavalerie, magiciens, sièges ;
- trois paliers technologiques clairs ;
- cartes avec forêts, montagnes, eau, ports et brouillard ;
- flottes, débarquements, raids économiques ;
- unités faciles à comprendre, décisions stratégiques difficiles.

**À créer de façon indépendante :**
- tout l'univers, les deux civilisations, leurs noms, emblèmes, voix et créatures ;
- silhouettes, animations, bâtiments, interface, cartes, musiques, dialogues et textes ;
- l'arbre exact des technologies et l'équilibrage ;
- les missions, les personnages et la dramaturgie.

L'objectif est une **parenté de sensations et de boucle de jeu**, non une reproduction de contenus protégés d'une autre œuvre.

---

## 20. Parcours métier : ce que chaque acteur doit pouvoir faire

### Joueur novice

1. Démarrer une mission et savoir immédiatement quel est l'objectif.
2. Cliquer un paysan, l'envoyer à une mine, construire une maison puis une caserne.
3. Comprendre pourquoi une unité est grisée : âge, bâtiment requis, population ou ressources.
4. Repérer un raid et envoyer ses troupes défendre la mine.
5. Apprendre la magie par un objectif simple, sans perdre une mission faute d'explication.

### Joueur expérimenté

1. Choisir une ouverture économique ou militaire sans progression scriptée obligatoire.
2. Surveiller ses pertes de paysans et priver l'adversaire de ressources.
3. Contourner une défense, exploiter une côte, préparer un siège.
4. Gérer plusieurs groupes et bâtiments de production.
5. Identifier les contres possibles à l'armée adverse et ajuster sa composition.

### Joueur de campagne

1. Comprendre pourquoi la mission compte pour son camp.
2. Voir les conséquences des batailles sur des lieux et des personnages récurrents.
3. Ressentir que les deux récits éclairent des vérités incompatibles.
4. Finir une campagne avec une réponse émotionnelle, même si le mystère reste partiellement ouvert.

### Spectateur

1. Distinguer instantanément les factions et la direction du conflit.
2. Reconnaître les grands événements sans connaître toutes les statistiques.
3. Lire le niveau d'évolution des bases et repérer les attaques décisives.

---

## 21. Critères d'acceptation métier pour une première tranche jouable

Ces critères décrivent ce qu'on doit **pouvoir observer dans le jeu**, pas comment le programmer.

1. Sur une carte terrestre, deux factions peuvent commencer avec un centre, quatre paysans, or et bois.
2. Un paysan peut récolter, déposer sa charge, construire et réparer.
3. Un joueur peut construire logements, caserne, scierie, champ de tir et tour de guet.
4. Chaque camp peut produire un homme de hache, un piquier et un archer.
5. Les unités se déplacent, combattent, subissent des dégâts et meurent ; les bâtiments peuvent être détruits.
6. Le brouillard masque correctement les positions non observées.
7. La population empêche le recrutement au-delà de la capacité, sans effacer les troupes existantes.
8. L'âge II peut être atteint avec les prérequis ; la forge, les gardes, cavaliers et sièges deviennent disponibles.
9. Une armée composée intelligemment de plusieurs rôles peut vaincre une force supérieure mais mal assortie.
10. Une partie se termine sur une condition de défaite/victoire intelligible.
11. Les deux factions utilisent leurs visuels, noms et textes distincts, tout en respectant les mêmes règles économiques de base.
12. Le temps d'une bataille n'est pas dicté par une scène narrative obligatoire.

**Deuxième tranche :** Écho, sanctuaires, mages, âge III, volants, deux ports et batailles navales. **Troisième tranche :** campagnes narratives complètes, scènes, variations de mission et modes supplémentaires.

Cette séquence est une proposition de **priorités métier**, non un plan technique.

---

## 22. Questions créatives volontairement ouvertes

À discuter avant de figer la version 1.0 :

1. **Ton général :** sombre et poignant, ou plus épique et chaleureux avec une pointe d'ironie ?
2. **Complexité des deux factions :** miroir presque parfait pour une première version, ou asymétrie modérée dès le départ ?
3. **Place de la mer :** élément incontournable des cartes et campagnes majeures, ou surtout une famille de cartes dédiées ?
4. **Niveau de fantasy :** un monde surtout humain avec créatures rares, ou armées fantastiques beaucoup plus présentes ?
5. **Coutures :** uniquement décor et objectifs au lancement, ou aussi mode spécial de combat ?
6. **Fin de campagne :** une conclusion commune mais nuancée, ou deux conclusions irréconciliables qui se répondent ?
7. **Nom de fiction :** conserver « La Guerre des Jours Effacés » comme sous-titre, ou chercher un intitulé plus mordant ?

---

## 23. Décisions proposées à conserver à ce stade

- **Titre de projet :** WarConquer.
- **Sous-titre de travail :** La Guerre des Jours Effacés.
- **Genre :** RTS médiéval-fantastique classique, avec histoire spéculative originale.
- **Factions initiales :** Couronne de Verre et Marches Délivrées.
- **Ressources :** or, bois, Écho ; logements comme limite de population.
- **Progression :** campement → bourg → citadelle.
- **Forces armées :** paysans, haches, piques, archers, infanterie lourde, cavalerie, sièges, soutien, magie, volants et flottes.
- **Modes prioritaires :** campagne, escarmouche ; multijoueur dans la vision du produit.
- **Ton :** conte guerrier sombre, fascinant, humain ; pas de fantasy générique ni de futurisme artificiel.
- **Règle d'or :** l'histoire donne du sens aux guerres, mais ne prend jamais le contrôle des décisions tactiques du joueur.

*Fin de la bible v0.1. Document littéraire et métier uniquement ; aucune technologie, moteur ou infrastructure n'y est prescrite.*
