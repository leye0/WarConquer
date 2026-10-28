# Contrat de manipulation : objet × personnage × animation

Le placement d'un objet tenu est une **interaction à trois sources** et non
une recherche de la partie la plus longue d'un maillage.

1. **Objet** : concept original, brief de génération, vues du GLB et analyse
   sémantique par vision. La vision nomme les régions de prise, les surfaces
   actives, leurs signes/directions et les points de référence. Une hache a un
   tranchant, un arc un avant et une corde, une arme à feu une bouche et une
   détente, un outil une zone de travail. Les noms de rôles sont des données
   ouvertes, pas une liste de rotations par classe d'arme.
2. **Personnage** : le rig fournit ses articulations, le repère des paumes,
   la main principale, les zones accessibles et les contraintes corporelles.
3. **Mixamo** : chaque clip réel fournit une phase et une pose animée. Le nombre
   de mains en contact et les prises peuvent changer entre transport, garde,
   utilisation, rechargement et retour au repos.

## Contrat à confirmer avant le fitting

Chaque objet doit avoir une caractérisation vision vérifiable et versionnée,
incluant au minimum :

- empreintes des sources et confiance, avec `needs_review` en cas d'ambiguïté ;
- type d'action, rôles fonctionnels nommés et direction de l'effet (origine,
  point/cible ou normale orientée, selon le rôle) ;
- région(s) de prise **sur l'objet**, avec points stratégiques certifiés ;
- modes d'interaction séparés, chacun indiquant une ou deux mains attendues,
  la main principale, la main secondaire éventuelle, les régions associées et
  le geste Mixamo recherché ;
- statut distinct pour la compatibilité du clip réel. Un nom d'animation ne
  démontre pas à lui seul que la main rejoint une zone de prise.

Le modèle peut proposer des modalités différentes pour le même objet : un arc
peut être porté d'une main et utilisé avec les deux ; une arme peut être
transportée, épaulée, tirée, puis rechargée avec des contacts différents.

Un mode `two_hands` exige deux contacts réels, donc un geste compatible et/ou
une correction IK du bras secondaire. Tant que ce contact n'est pas démontré,
le statut doit rester `secondary_hand_unresolved`, pas `fully_ready`.

## Ce que la géométrie a le droit de faire

- Reprojeter **un point déjà nommé par la vision** sur la surface du GLB.
- Aligner des repères 3D et produire une transformation rigide sans reflet.
- Mesurer distances aux paumes, collisions, proportions et continuité des
  contacts à plusieurs frames de chaque clip.

Elle ne doit **jamais** décider qu'une extrémité est une lame, une tête, une
bouche, un manche ou l'avant d'un arc à partir de PCA, longueur, largeur,
centroïde, densité des sommets ou orientation du GLB.

Une annotation trop éloignée du vrai maillage, ambiguë en profondeur, ou
contradictoire entre vues bloque la calibration et demande une révision
sémantique. Déplacer automatiquement le point vers une extrémité jugée
probable est interdit. La PCA reste autorisée pour orienter les **caméras**
et mesurer des dimensions, jamais pour attribuer une fonction à un sommet.

## Validation en deux temps

1. **Avant le GLB/fitting** : confirmer les fonctions, les prises attendues et
   les modalités avec les visuels de l'objet et du personnage et les métadonnées
   des mouvements disponibles. Ne pas déclarer Mixamo `verified` à ce stade.
2. **Après import du clip réel** : échantillonner les articulations et le
   maillage à travers l'animation, puis vérifier les contacts primaires,
   secondaires, surfaces actives et collisions. Enfin soumettre les rendus à
   une QA visuelle indépendante. Un rejet précise **quel contrat** a échoué ;
   il ne déclenche pas une autre rotation arbitraire.

Les plans de prise historiques à schéma 2/3 ne possèdent pas encore ce contrat
complet à trois sources. Ils ne doivent pas être présentés comme une preuve de
compatibilité à deux mains. Toute migration doit conserver les reçus payants
et exiger l'autorisation explicite avant un nouvel appel de vision.
