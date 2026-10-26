# Examen du cadrage — vidéo SW v2

Date : 26 octobre 2026. Exécution : [GitHub Actions 40384864611](https://github.com/leye0/WarConquer/actions/runs/40384864611).

**But :** corriger le défaut vérifié sur la première vidéo, dans laquelle la tête de la hache disparaissait au-dessus de l'image lors d'une attaque vers 4,5 secondes.

## Résultat

- [Vidéo v2 MP4](SW-walk-then-attack-framed.mp4) : huit secondes, une marche SW puis des attaques SW.
- [Images de contrôle](contact-sheet.jpg) : huit prélèvements répartis dans les phases marche (0–4 s) et attaque (4–8 s).
- [Première image fortement élargie](reference-SW-padded-768.png) : personnage à 35 % de la hauteur de la référence, initialement placé à 61 % de largeur, avec les pieds à 78 % de hauteur.
- [Métadonnées](job.json) : modèle `x-ai/grok-imagine-video-1.5-lite`, coût déclaré **0,17 USD**, clip effectivement reçu sur `main`.

**Contrôle de coupure : réussi pour ce test.** Le contrôle image par image à quatre prélèvements par seconde (32 images, MP4 544 × 544) n'a détecté **aucune zone sombre/colorée touchant les bandes extérieures du cadre** selon le seuil défini. L'inspection visuelle de la planche confirme que la hache levée lors des attaques à ~4,6 s et ~6,6 s se trouve entièrement dans le cadre.

**Réserve majeure :** le personnage **augmente nettement d'échelle** entre le début de la marche (~0,6 s) et la fin (~3,6 s), bien que le prompt impose une caméra fixe et une échelle stable. Il peut s'agir d'un zoom implicite ou d'une dérive de taille du générateur. Ce n'est **pas** un plan de sprite à échelle constante utilisable tel quel.

L'objectif principal de la seconde tentative (éviter la coupe de l'arme) est atteint, mais la vidéo reste **brouillon non approuvé** et doit être jugée par l'utilisateur. Ne pas lancer de régénération payante supplémentaire sans en avoir besoin. Le MP4 précédent reste conservé sous `assets/experiments/video-sw/` pour comparaison.
