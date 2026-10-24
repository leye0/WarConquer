# WarConquer — Direction visuelle et inventaire de concepts

## Fiches d'apparence physique — v0.1 (travail en cours)

Ce document complète la [bible du jeu](game-bible.md), le [codex](unit-building-codex.md) et les [doctrines des factions](faction-strategy.md). Il fixe **les caractéristiques visuelles des 68 sujets** prévus : 24 unités terrestres/volantes, 8 navires et 36 apparences de bâtiments. Le terrain est volontairement exclu.

Les PNG produits se trouvent progressivement dans `assets/concepts/<faction>/<type>/<identifiant>.png`. Un chemin listé ci-dessous est une **cible d'illustration**, pas nécessairement un fichier déjà généré.

## Règles communes

- **Type :** illustration conceptuelle autonome pour un RTS médiéval-fantastique. Ni modèle 3D prêt à importer, ni feuille d'animation, ni terrain.
- **Caméra :** vue de trois quarts légèrement plongeante ; silhouette entière centrée et isolée.
- **Fond :** véritable transparence alpha, sans sol, décor, socle ni interface.
- **Finition :** 2D peinte à la main, détails crédibles du métal, du cuir, du bois et des tissus, proportions lisibles à petite taille.
- **Couronne de Verre :** bleu nuit, ivoire, bronze, pierre claire, découpes structurées, matériaux entretenus mais utilisés.
- **Marches Délivrées :** rouge oxyde, noir de suie, cuivre patiné, cuir réparé, bois noirci, rubans et noms cousus.
- **Originalité :** pas de reproduction des personnages, emblèmes, bâtiments ou visuels d'une licence existante.
- **Composition des unités :** exactement un sujet par PNG ; personnage et arme entiers dans le cadre.
- **Composition des navires :** un navire isolé vu d'en haut en diagonale, sans eau ; coque et gréement visibles.
- **Composition des bâtiments :** édifice complet isolé, sans tuile de terrain ; portes, toiture et fonction identifiables.

Les illustrations sont des **concepts statiques**. Le passage à des sprites animés, différentes orientations, variantes de destruction, dimensions de cases et palettes de joueurs sera une étape distincte.

## Catalogue des 68 apparences

### Couronne de Verre

#### Unités terrestres et volantes

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Paysan du Sceau | human field worker, tousled brown hair, sturdy linen ivory shirt, midnight-blue sleeveless surcoat, bronze girdle, leather boots, wooden identity tablet, axe and bound firewood | `assets/concepts/couronne/units/paysan.png` |
| Homme de hache | athletic human militia wood-guard, blue linen gambeson over chain shirt, bronze-edged round wooden shield, practical one-handed crescent axe, short dark hair, practical kettle helmet | `assets/concepts/couronne/units/hache.png` |
| Piquier de garnison | lean human frontier guardsman, long ashwood pike tipped with steel, blue-and-ivory quilted armor, open kettle helm, small strapped buckler, grounded anti-cavalry stance | `assets/concepts/couronne/units/piquier.png` |
| Archer des Veilles | human precision longbowman, tall elegant yew longbow, ivory blue hooded cape, bronze-braced bracer, neat quiver, leather padded jacket, disciplined ready-to-shoot posture | `assets/concepts/couronne/units/archer.png` |
| Garde du Sceau | armored human heavy infantry with tall ivory bronze-edged rectangular shield, weathered deep-blue surcoat over articulated steel scale plates, broad short sword, closed bronze visor | `assets/concepts/couronne/units/garde_lourd.png` |
| Chevalier des Cloches | disciplined mounted knight on powerful chestnut warhorse, blue-and-ivory caparison with small bronze bells, lance couched forward, bronze-trimmed full helmet, heavy believable horse armor | `assets/concepts/couronne/units/cavalier.png` |
| Lance-pierres de bronze | compact medieval wheeled torsion stone-thrower made of oak timber, bronze bearings, thick rope winding arms, one single large stone ammunition, detailed mechanical silhouette, no crew | `assets/concepts/couronne/units/catapulte.png` |
| Bélier du Palais | heavily reinforced covered ram on four sturdy wheels, angled navy textile and bronze-plated canopy, huge oak log tipped with cast bronze ram-head, no crew | `assets/concepts/couronne/units/belier.png` |
| Chapelain des Preuves | male human battlefield cleric-healer in ivory robe with midnight blue mantle, leather surgeon satchel, bronze medical bell and sealed parchment roll, no weapons, calm face | `assets/concepts/couronne/units/chapelain.png` |
| Archiviste de guerre | human arcane scholar of battlefield records, long dark-blue coat with ivory calligraphic hems, bronze clasps, satchel of scrolls, floating translucent geometric seal above open palm, alert stern expression | `assets/concepts/couronne/units/archiviste.png` |
| Vigile de verre | original fantasy aerial creature like broad-winged griffin with translucent smoky-blue glass-like feathers, bronze harness carrying tiny cloaked observer, elegant birdlike head and strong talons, no saddle banners | `assets/concepts/couronne/units/vigile.png` |
| Conservateur de Sceau | elite human anti-magic foot guardian, layered ivory-bronze plate armor over midnight blue tabard, massive ward reliquary on forearm glowing through tinted glass, broad protective sword, heavy grounded stance | `assets/concepts/couronne/units/conservateur.png` |

#### Navires

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Nef de passage | medieval wooden troop transport ship with wide central open cargo deck, stout brown hull, midnight blue rectangular sail with ivory stripe, bronze fittings, oars visible, no crew | `assets/concepts/couronne/ships/transport.png` |
| Patrouilleur de verre | sleek fast medieval war galley, sharp bow, blue sail with minimal ivory diagonal, bronze forward ballista, many oars and reinforced rails, no crew | `assets/concepts/couronne/ships/escorte.png` |
| Dragueur de sel | practical low draft wooden workboat with bronze dredging winch, net basket of pale luminous Echo crystals, compact deep-blue sail, worn utility hull, no crew | `assets/concepts/couronne/ships/dragueur.png` |
| Galéasse du Sceau | massive late-medieval fantasy heavy coastal artillery galley, armored high-sided hull, bronze bombard ballista on foredeck, double blue sails, ornate but credible seaworthy ship, no crew | `assets/concepts/couronne/ships/artillerie.png` |

#### Bâtiments

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Maison du Sceau | modest one-story town hall with light limestone foundation, oak roof beams, blue cloth awning, one bronze bell, visible storehouse doors and a small blue pennant | `assets/concepts/couronne/buildings/centre_i.png` |
| Halle des Registres | medium fortified civic hall with pale stone walls, tall pointed blue tile roof, open bronze-trimmed ledger portico, two bell turrets, attached storage wing | `assets/concepts/couronne/buildings/centre_ii.png` |
| Palais des Veilles | grand but compact medieval fortified administrative palace, pale limestone terraces, rich midnight-blue steep roofs, stained-glass windows, multiple bronze bells, strong central tower | `assets/concepts/couronne/buildings/centre_iii.png` |
| Maison de pierre | small lived-in medieval stone cottage with ivory lime plaster, blue fabric shutters, short chimney, brown shingle roof, stack of firewood by entry | `assets/concepts/couronne/buildings/maison.png` |
| Caserne | rectangular pale-stone military barracks, drill yard enclosed by low walls, rows of spears and axes at entry, blue and ivory banner, bronze bell at portal | `assets/concepts/couronne/buildings/caserne.png` |
| Scierie | open timberwork sawmill with bronze-framed saw bench, stacks of cut lumber, waterwheel-like mechanical pulley, neat blue work apron hanging, no surrounding terrain | `assets/concepts/couronne/buildings/scierie.png` |
| Champ de tir | medieval archer training pavilion with blue roof, stacked yew bows, quiver racks, two straw circular targets attached within compact fenced yard | `assets/concepts/couronne/buildings/champ_tir.png` |
| Dépôt | simple logistical storehouse with low limestone wall, dark-blue tarp roof, wooden doors, crates of ore and wood, sturdy bronze scale hanging at entrance | `assets/concepts/couronne/buildings/depot.png` |
| Tour de guet | slender pale stone defensive watchtower with blue conical roof, bronze bell hanging under eaves, battlements and arrow slit, clear silhouette | `assets/concepts/couronne/buildings/tour.png` |
| Forge du Sceau | stone and bronze smithy with dark slate roof, heavy anvil, bright orange forge hearth inside open arch, sword and shield hung outside, short smokestack | `assets/concepts/couronne/buildings/forge.png` |
| Écurie | large pale limestone horse stable with deep-blue tiled roof, timber doors, water trough, saddle racks, small bronze horse bell, no animals outside | `assets/concepts/couronne/buildings/ecurie.png` |
| Atelier de siège | broad open military engineering barn, sturdy oak roof, spare catapult wheels and huge timber beams, bronze pulleys, tools and thick ropes | `assets/concepts/couronne/buildings/atelier_siege.png` |
| Sanctuaire | small solemn medieval chapel with ivory limestone, deep-blue glass windows, round bronze bell, sheltered healer porch with hanging linen | `assets/concepts/couronne/buildings/sanctuaire.png` |
| Puits d'Écho | stone extraction structure around a hexagonal luminous pale crystal vein, bronze winch and suspended bucket, blue protective tarp canopy, controlled magical machinery | `assets/concepts/couronne/buildings/puits_echo.png` |
| Port militaire | compact elevated dock structure on timber piles with blue-roofed dock office, loading crane, stacked barrels and rope, wooden jetty ending cleanly, no water or shore terrain | `assets/concepts/couronne/buildings/port.png` |
| Observatoire | tall arcane study tower of pale limestone with bronze astrolabe armature, midnight-blue pointed roof, narrow stained-glass windows, floating faint geometric seals | `assets/concepts/couronne/buildings/observatoire.png` |
| Aire des Vigiles | compact military aviary/landing tower with open bronze-framed terrace, blue canvas roofs, perches for translucent-wing creatures, no creature present | `assets/concepts/couronne/buildings/nid_volant.png` |
| Remparts et portes | self-contained modular fortification segment, pale stone crenellated wall with central closed oak gate bound by bronze, blue banners, short wall ends, no terrain | `assets/concepts/couronne/buildings/remparts.png` |

### Marches Délivrées

#### Unités terrestres et volantes

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Paysan des Veillées | weathered capable forest village farm worker, charcoal black linen patched with oxblood-red cloth and copper stitching, brown leather boots, tied hair, wooden name tablet, small axe and bundle of firewood | `assets/concepts/marches/units/paysan.png` |
| Fendeur de racines | robust forest axeman from displaced settlements, layered soot-black leather and patched dark-red wool, bare forearms wrapped with copper-thread bandages, long two-handed splitting axe, forceful stance | `assets/concepts/marches/units/hache.png` |
| Porte-épieu | rangy caravan defender, ashwood spear with rugged iron head, rough dark red linen shoulder cloak, mismatched layered leather armor, small angular wooden shield, purposeful defensive stance | `assets/concepts/marches/units/piquier.png` |
| Archer aux fils rouges | agile forest huntress, compact recurve bow in hand, charcoal hood with oxblood-red woven ties, copper thread winding down bracer, asymmetrical leather quiver, poised to retreat | `assets/concepts/marches/units/archer.png` |
| Porte-muraille | stocky veteran with broad patched rectangular shield built from dark iron-bound planks, red-threaded worn chain-and-wood armor, practical cleaver sword, determined defensive stance | `assets/concepts/marches/units/garde_lourd.png` |
| Cavalier des Cerfs-brasiers | swift rider on large believable red-brown fantasy stag with subtle cold ember glow inside magnificent antlers, rider in dark leather and frayed red cloak, short spear and curved bow, no flames | `assets/concepts/marches/units/cavalier.png` |
| Catapulte des Vestiges | patched wheeled counterweight catapult of blackened timber, copper rivets, scarlet binding cords and stone counterweight bearing faded carvings, one stone projectile, no crew | `assets/concepts/marches/units/catapulte.png` |
| Bélier-racine | massive root-entangled oak log ram on rough wooden wheels, low slanted hide canopy with red stitched bindings, rugged copper striking tip, no crew | `assets/concepts/marches/units/belier.png` |
| Ravaudeuse | older female village healer with gray hair tied in copper thimbles, patched charcoal robe with winding dark-red memory cords, linen medical wraps and bone needle bundle, compassionate weathered face, no weapons | `assets/concepts/marches/units/ravaudeuse.png` |
| Tisseur des Possibles | unsettling male or androgynous adult sorcerer in soot-black layered coat and deep-red ribbon wraps, copper talismans and name strips, several fine suspended crimson filaments pulled between fingers, no weapon | `assets/concepts/marches/units/tisseur.png` |
| Grand Miroir-de-nuit | original large flying nocturnal feathered animal, broad matte black-violet wings reflecting faded ghostly silver memory silhouettes, narrow avian face, strong talons, no rider, not a dragon | `assets/concepts/marches/units/vigile.png` |
| Passe-Nom | lean elite infantry infiltrator clad in charcoal leather and red woven cloth strips, dark half-mask of carved wood, compact recurved blade and small engraved name tablet, stealthy cautious crouch, visibly mortal | `assets/concepts/marches/units/passe_nom.png` |

#### Navires

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Barge cousue | wide rough medieval troop barge made of repaired dark timber with visible copper staples and stitched red sail, open troop deck and reinforced ramp, no crew | `assets/concepts/marches/ships/transport.png` |
| Brise-écume | swift narrow medieval river-and-sea raiding vessel, black wood with copper ribs, triangular dark-red sail, light front bolt thrower, many slim oars, no crew | `assets/concepts/marches/ships/escorte.png` |
| Chaloupe des Brumes | low blackened timber work skiff with red-brown patched sail, simple copper dredging cradle full of faintly luminous white Echo crystals, rope reels, no crew | `assets/concepts/marches/ships/dragueur.png` |
| Arche de Cendre | heavy fantasy war-barge of layered dark wooden hulls and copper binding, enormous forward stone-launching siege contraption, broad dark-red stitched sails, intimidating practical silhouette, no crew | `assets/concepts/marches/ships/artillerie.png` |

#### Bâtiments

| Nom | Apparence physique à respecter | Fichier cible |
| --- | --- | --- |
| Foyer des Noms | rough but welcoming timber settlement hall built around an ancient preserved tree trunk, oxblood fabric ribbons of names, fire bowl in entrance porch, low black-wood roof | `assets/concepts/marches/buildings/centre_i.png` |
| Halle des Braises | expanded black-timber communal hall, deep red patchwork roof, carved timber columns and courtyard fire brazier, hundreds of short memory cords, no terrain | `assets/concepts/marches/buildings/centre_ii.png` |
| Cœur des Marches | magnificent original forest citadel of intricately bound black oak structures and dark copper towers, broad scarlet patchwork banners, ancient living tree integrated into central keep | `assets/concepts/marches/buildings/centre_iii.png` |
| Maison des Veillées | small dark-wood village cottage with patched reddish thatch roof, narrow copper window frame, smoke chimney, hanging name ribbons and firewood pile | `assets/concepts/marches/buildings/maison.png` |
| Cercle des Haches | open ring-like timber warriors barracks with rough black beams, red woven canopy, axe racks and spears along railings, central packed training yard as part of structure | `assets/concepts/marches/buildings/caserne.png` |
| Atelier de Racines | rugged forest sawmill of dark timber with copper hand-saw station, root-carved pulleys, piles of rough planks and red fabric tied on posts, no terrain | `assets/concepts/marches/buildings/scierie.png` |
| Butte des Flèches | compact wooden archery range with woven red roofs, curved twig fencing, rough straw targets and quiver racks, short platform and training path | `assets/concepts/marches/buildings/champ_tir.png` |
| Grenier de route | sturdy portable-looking dark-timber supply barn with red canvas cover, sacks, ore baskets and stacks of firewood, copper latch, no wheels | `assets/concepts/marches/buildings/depot.png` |
| Vigie cousue | tall asymmetrical dark wooden watchtower braced with copper straps, red ribbon streamers and small hanging bells, open archer gallery, no terrain | `assets/concepts/marches/buildings/tour.png` |
| Forge des Cendres | low black stone and dark timber smithy, glowing ember hearth, rough copper forge bellows, heavy anvil, red ropes binding roof timbers | `assets/concepts/marches/buildings/forge.png` |
| Cour des Montures | open stable complex for giant stag mounts, dark timber palisade, red patched awning, feeding troughs and antler-shaped copper hooks, no animals | `assets/concepts/marches/buildings/ecurie.png` |
| Atelier des Brisures | large blackwood siege carpenter workshop with red canvas patched roof, spare wagon wheels, root-bound logs, copper tools and counterweights | `assets/concepts/marches/buildings/atelier_siege.png` |
| Maison des Ravaudeuses | solemn small dark wooden healing house with reddish fabric roof, numerous hanging memory threads, copper needles and woven medicine baskets at entry | `assets/concepts/marches/buildings/sanctuaire.png` |
| Puits de Souvenir | rough dark-stone extraction well built around pale luminous Echo crystal seam, root-wrapped wooden hoist and copper-lined buckets, red protective cloth | `assets/concepts/marches/buildings/puits_echo.png` |
| Grève des Barques | rustic pier of black weathered timber, red canvas boat shed, copper rope hooks, stacks of barrels and ropes, wooden jetty only with no water | `assets/concepts/marches/buildings/port.png` |
| Cercle des Possibles | open dark-copper arcane ring tower supported by twisted black timber beams, suspended red thread lattice and faint ghostly geometric silhouettes, no terrain | `assets/concepts/marches/buildings/observatoire.png` |
| Nid des Murmures | fantasy dark-wood aviary tower with sweeping curved roof like bird wings, red fabric streamers, broad sheltered perches for night wing creatures, no creatures | `assets/concepts/marches/buildings/nid_volant.png` |
| Palissades et portes | self-contained modular sturdy blackened wood palisade section with central closed heavy gate, copper bindings, woven dark-red warning pennants, short wall ends, no terrain | `assets/concepts/marches/buildings/remparts.png` |

## Validation d'une illustration

1. Sujet physiquement complet, sans arme, aile, voile ni tour coupée par le bord.
2. Fond réellement transparent et aucun décor indésirable.
3. Palette de la bonne faction et matériaux compatibles avec le codex.
4. Silhouette distincte du paysan, de l'archer, du garde et des autres familles.
5. Bâtiment identifiable à sa fonction sans avoir besoin de lire son nom.
6. Absence de lettrage inventé, de logo et de référence reconnaissable à d'autres univers.
7. Pour les bâtiments, vue et volume cohérents avec les autres illustrations, sans imposer encore une grille de jeu.

## Ce qu'il restera à détailler plus tard

- orientations animées de chaque unité et de chaque bâtiment ;
- poses de marche, attaque, récolte, construction, mort et soin ;
- animation de recrutement, amélioration, dommages et destruction des bâtiments ;
- sprites finalisés et réduits aux dimensions exactes du moteur ;
- variantes de couleur d'équipe, portraits de commandes et mini-icônes ;
- terrain, routes, forêts, minerais, côtes, eau et relief (explicitement hors périmètre aujourd'hui).

**Source de vérité :** ce fichier pour l'apparence ; les autres bibles pour le rôle militaire et narratif. Une illustration qui contredit les règles doit être corrigée avant son adoption comme référence finale.
