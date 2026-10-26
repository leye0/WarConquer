# WarConquer — guides de sprites directionnels (Brouillons)

Ces fichiers SVG sont des **templates de pose originaux**, non des sprites finaux, ni des copies de pixel art.

## Contraintes

- Les sprites finaux seront **illustrés, détaillés, haute définition et anti-aliasés** ; le projet utilise la technique des sprites pour l'animation, **pas le pixel art**.
- Les planches de Warcraft II (Footman / Grunt; Knight / Ogre; Peasant / Peon; Elven Archer / Troll Axethrower) servent uniquement à observer des **conventions fonctionnelles de RTS** (rythme, lisibilité, orientation, préparation/impact/récupération) ; aucun pixel ni traçage n'est repris.
- 8 orientations dessinées séparément, sans symétrie d'image. Les bras anatomiques sont repérés en bleu (gauche) et corail (droite).
- Chaque cellule doit garder le même point d'ancrage au sol, la même échelle de personnage, un cadrage sans rognage et un équipement du bon côté.
- **Statut : DRAFT / validation humaine requise.** Ces silhouettes procédurales ne sont pas approuvées ; les articulations, mouvements et chevauchements doivent être inspectés visuellement avant toute génération payante.
- Aucun rendu Muse ou OpenRouter n'est lancé par ces fichiers ; préserver le pipeline existant et éviter les appels payants avant validation.

## Planches

- [00-overview.svg](../assets/sprite-templates/00-overview.svg) : familles et orientations.
- **MÊLÉE LÉGÈRE** : [marche](../assets/sprite-templates/light-walk.svg) (8×8) · [action](../assets/sprite-templates/light-action.svg) (8×6).
- **MÊLÉE LOURDE** : [marche](../assets/sprite-templates/heavy-walk.svg) (8×8) · [action](../assets/sprite-templates/heavy-action.svg) (8×6).
- **OUVRIER** : [marche](../assets/sprite-templates/worker-walk.svg) (8×8) · [action](../assets/sprite-templates/worker-action.svg) (8×6).
- **DISTANCE** : [marche](../assets/sprite-templates/ranged-walk.svg) (8×8) · [action](../assets/sprite-templates/ranged-action.svg) (8×6).

## Vérifications requises

1. Tester la correspondance N/NE/E/SE/S/SW/W/NW avec les axes de déplacement à l'écran.
2. Vérifier physiquement la latéralité (épée, outil, arc, bras, équipements) pour chaque orientation : aucun basculement miroir.
3. Observer la lecture temporelle de chaque rangée, la continuité des contacts au sol et l'absence de rognage : les planches ne sont **pas** approuvées sans cette étape.
4. Soumettre les planches au propriétaire du projet pour corrections/approbation. **Ne pas remplacer par du pixel art.**
