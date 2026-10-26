# QA — pipeline complet de personnage, 26 octobre 2026

**Statut : EXÉCUTION TECHNIQUE RÉUSSIE; RÉSULTATS VISUELS NON APPROUVÉS.**

- [Planche des huit images Muse](review-8-directions.png) : huit PNG indépendants à 1024×1024 px, images fixes seulement, référencées dans [stills](stills/).
- [Rapport de génération](report.json) : **8 images/8**, **8 vidéos/8**, **coût OpenRouter rapporté : 1,44 $ US** (environ 0,08 $ pour Muse et 1,36 $ pour Grok vidéo).
- [Action complète](https://github.com/leye0/WarConquer/actions/runs/40390139497) : toutes les données enregistrées dans la branche `main`; checkpoint des images, des IDs de jobs vidéo et des MP4. 
- **Tous les résultats restent des brouillons.** Aucun test statistique ne confirme qu’un corps entier fait réellement face à la direction demandée.

## Vidéos, contacts et observations

Chaque vidéo dure **8 secondes** (cible : 0–4 s marche, 4–8 s attaque), 480p, première image basée sur la vue correspondante, caméra supposée fixe. Les métriques sont des **heuristiques** basées sur 32 captures par vidéo : le taux d'images en contact avec le bord peut inclure de la texture ou des accessoires et ne prouve pas à lui seul une coupure. Le rapport de hauteur peut également varier lors d’une frappe.

| Dir. | Vidéo | Contact sheet | Alertes au bord (sur 32) | Rapport hauteur max/min | Observation visuelle |
| --- | --- | --- | ---: | ---: | --- |
| **N** | [MP4](videos/N/walk-then-attack.mp4) | [8 images](videos/N/contact-sheet.jpg) | 6 | 2.163 | Marche lisible; changement d’échelle marqué; vérifier les contacts au cadre durant l’attaque. |
| **NE** | [MP4](videos/NE/walk-then-attack.mp4) | [8 images](videos/NE/contact-sheet.jpg) | 0 | 1.281 | Marche lisible; dans la phase d’attaque le guerrier tourne parfois vers l’arrière / change la présentation de la hache. |
| **E** | [MP4](videos/E/walk-then-attack.mp4) | [8 images](videos/E/contact-sheet.jpg) | 4 | 1.330 | Attaque fait tourner le torse vers la caméra; le profil E n’est pas conservé. |
| **SE** | [MP4](videos/SE/walk-then-attack.mp4) | [8 images](videos/SE/contact-sheet.jpg) | 5 | 2.197 | Image immobile très proche de E au lieu du vrai 3/4 avant-droit; vidéo avec grande dérive d’échelle. |
| **S** | [MP4](videos/S/walk-then-attack.mp4) | [8 images](videos/S/contact-sheet.jpg) | 5 | 2.660 | Marche grossit très fortement; à environ 5,6 s, tête de hache coupée à droite sur la planche. |
| **SW** | [MP4](videos/SW/walk-then-attack.mp4) | [8 images](videos/SW/contact-sheet.jpg) | 3 | 2.118 | Image initiale tourne vers la droite, presque comme SE; la marche passe vers une vue frontale plutôt que SW. |
| **W** | [MP4](videos/W/walk-then-attack.mp4) | [8 images](videos/W/contact-sheet.jpg) | 1 | 1.451 | La marche W ressemble à une marche de profil; attaque change momentanément le torse vers la caméra. |
| **NW** | [MP4](videos/NW/walk-then-attack.mp4) | [8 images](videos/NW/contact-sheet.jpg) | 5 | 1.267 | Bonne lecture globale dos-gauche au début; l’attaque retourne le buste et semble couper l’arme à certains instants. |

### Conclusions

**Le système de création est complet et fonctionnel**, mais **le rendu n'est pas suffisamment fiable pour générer des sprites d’animation utilisables directement**.

1. **Images fixes** : N, W, E et NW sont lisibles comme directions différentes, mais **SW et SE ne sont pas assez distinguables** (les corps se présentent trop vers la droite). La règle « rotation de l’ensemble du corps » est dans les prompts; Muse ne la respecte pas systématiquement.
2. **Vidéos** : chaque vidéo montre une marche suivie d’une attaque; cependant plusieurs modèles ont **dévié l’orientation pendant les attaques**. Le cadrage de la hache n'est pas assuré pour toutes les directions.
3. **Caméra** : l’échelle apparente change sensiblement dans plusieurs vidéos malgré l’insistance sur une caméra fixe; une normalisation a posteriori peut aider si le sujet n'est pas rogné, mais ne récupère pas les pixels manquants lorsqu'une hache est déjà hors de l'image.
4. **Contrôles** : 7 vidéos sur 8 ont au moins un signal de contact au bord; 6 vidéos sur 8 dépassent le seuil indicatif 1,30 de dérive d'échelle. Ce sont des **avertissements de vérification**, pas des verdicts biomécaniques.

### Suites techniques envisageables

- Introduire une **validation humaine entre la génération des huit vues et les huit vidéos** pour ne pas payer de vidéos à partir de mauvaises orientations.
- Renforcer la correction des vues SW et SE **sur le corps complet et la direction des pointes de bottes**; ne pas relancer les huit directions par défaut lorsque seules une ou deux doivent être corrigées.
- Pour la vidéo, comparer un modèle plus obéissant au **transfert de mouvement** ou découper marche / attaque en deux clips distincts avant assemblage; la demande d’un unique clip huit secondes avec deux actions encourage les changements de caméra.
- Pas de relance automatique des appels payants. Reprendre les fichiers existants et leurs métadonnées.

**Ce bilan ne modifie pas les versions déjà approuvées dans `assets/experiments/standing-turnaround/marches_hache/`**, notamment le NW remplacé avec ton accord.
