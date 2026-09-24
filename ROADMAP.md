# Feuille de route

Ce qui reste à faire, et ce qu'on sait déjà de chaque chose. C'est une **liste**,
pas un plan : rien ici n'est ordonné par priorité et rien n'est engagé.

Chaque entrée porte les mesures déjà prises, pour qu'on puisse la reprendre
sans refaire le diagnostic. Les entrées marquées **décision** ne sont pas des
défauts à corriger : ce sont des choix à trancher, où le pipeline fait
aujourd'hui ce qu'on lui a demandé de faire.

> État au 24 septembre 2026 : 105 des 128 séquences du répertoire sont
> jouables, 5 792 mesures dont 3 263 jouables (56,3 %). Le détail de ce qui
> est écarté vit dans [`packages/transcription/HELD-BACK.md`](packages/transcription/HELD-BACK.md),
> qui est généré et ne peut pas vieillir.

---

## 1 · Lecture et son

### L1 — Revoir la fonctionnalité de lecture

Ce qu'elle fait aujourd'hui, pour servir de base à la revue :

- ordonnancement par anticipation contre l'horloge audio, pas contre React
  (réveil toutes les 25 ms, fenêtre de 150 ms)
- choix d'une plage de mesures, boucle, métronome, tempo réglable
- ouverture au tempo imprimé sur la partition quand il y en a un, proposé en
  un bouton dès qu'on s'en écarte
- la nuance en vigueur est propagée depuis la dernière imprimée, y compris
  quand on démarre au milieu d'un passage
- les mesures douteuses sont jouées quand même, et signalées à l'écran

Ce qui n'existe pas : pas de décompte avant départ, pas de ralenti progressif,
pas de répétition en boucle avec accélération, pas de mise en évidence de la
note en cours (seule la mesure est suivie).

### L2 — Revoir quels sons utiliser

Aujourd'hui tout est **synthétisé**, pas échantillonné : une salve de bruit
filtrée en passe-bande pour la caisse, une onde carrée pour le clic. Le choix
était délibéré — on écoute une transcription pour l'attraper en défaut, donc
ce qui compte est que les *différences* soient nettes, pas que la caisse soit
crédible.

Ce que le son rend actuellement :

| écrit sur la page | ce qu'on entend |
| --- | --- |
| nuance (`p` … `fff`) | niveau du passage, échelle compressée |
| accent, marcato, tap, ghost | écart **par rapport à** ce niveau |
| tête en croix, cercle, losange | fréquence du passe-bande (cross-stick, rimshot, cercle) |
| agrément (flam, drag, ruff) | frappes placées **avant** le temps |
| roulé buzz | remplissage dense de la durée écrite |
| diddle (barre sur la hampe) | deux frappes |
| main gauche / droite | **rien** — non utilisé |

À décider : rester synthétique ou passer à des échantillons, et que faire de
la main (panoramique ? rien ?).

---

## 2 · Les mesures

### M1 — Finir les corrections de mesures

**1 062 mesures (18,3 %) dont les durées ne bouclent pas.** C'était 44,5 % en
début de parcours ; dix causes distinctes ont été trouvées et corrigées, aucune
deux fois la même. Ce qui reste est une longue traîne sans coupable unique.

La méthode qui marche : prendre **une** mesure fautive, la découper de son PDF
avec ses coordonnées (`bar.py` dans le bac à sable le fait), et comparer ce que
la page montre à ce qu'on en a lu. Aucun script global n'a jamais trouvé ces
causes — la ligne de portée avalée par une ligature ne se voit qu'en constatant
qu'une « mesure » de 26 points de large n'est pas une mesure.

**Une part n'est pas corrigible** : ce sont des relevés faits à l'oreille par
des amateurs, et ils se trompent aussi. Une mesure à 4/4 du catalogue contient
une demi-pause et un soupir, point. Le pipeline a raison de la signaler ; il
n'y a rien à réparer de notre côté.

Le reste du tableau, pour situer :

| | mesures |
| --- | --- |
| jouables | 3 263 (56,3 %) |
| **somme fausse** | **1 062 (18,3 %)** |
| que des silences (vérifiées, muettes) | 844 (14,6 %) |
| sans métrique | 342 (5,9 %) |
| lues à l'espacement | 142 (2,5 %) |
| vides | 78 (1,3 %) |
| symbole inconnu | 61 (1,1 %) |

---

## 3 · Le sticking

### S1 — **décision** : les frappes sans lettre de main

**27 938 frappes sur 42 261 portent une main (66,1 %).** La répartition par
mesure est l'information utile :

- 2 176 mesures **entièrement** annotées
- 1 791 mesures **partiellement** annotées
- 533 mesures **pas du tout**

Vérifié en découpant une mesure partielle (`2019-full-show`, mesure 128) :
elle contient **seize doubles croches et la page n'imprime qu'un seul « R »**,
au départ du trait. Le reste est sous-entendu — *commence à droite, alterne*.

**Notre lecture est donc juste : c'est la page qui n'écrit pas.** Trois
séquences n'en portent aucune, onze en portent pour chaque note.

Le modèle a déjà une position là-dessus, écrite dans `packages/core/src/stroke.ts` :

> « L'absence signifie *la source ne le dit pas*, et non une valeur par
> défaut. Une transcription qui ne note pas le sticking ne doit pas être
> indiscernable d'une qui le noterait tout à la main droite, sinon
> l'application enseigne un doigté que personne n'a écrit. »

Les options :

1. **Ne rien faire.** L'absence reste une absence. Cohérent avec le principe
   ci-dessus, et honnête. Mais 34 % des frappes restent muettes à l'écran.
2. **Déduire l'alternance** : après une lettre imprimée, alterner jusqu'à la
   suivante. C'est ce qu'un batteur fait réellement — mais un diddle ou un
   flam rompt l'alternance, donc la déduction se trompera parfois.
3. **Déduire, et le montrer comme déduit** (lettres en gris, par exemple).
   Garde la distinction que le modèle protège tout en rendant le doigté
   lisible. C'est la seule option qui ne contredit pas `stroke.ts`.

---

## 4 · Les 23 séquences écartées

### A1 — Chiffrage tracé, imprimé mais non lu · 2 séquences

`2017-opener-8` (6/4), `2019-snare-break-early-season-2` (4/4). Vérifié à
l'œil : le chiffrage est bien imprimé. Leurs chiffres sont des contours absents
du vocabulaire `Drawn`. **Courte** : étendre la planche de contact des tracés.

### A2 — **décision** : aucun chiffrage imprimé · 6 séquences

`1993-drum-break`, `2014-solo-1`, `2017-movement-3-5`,
`2017-opening-snare-break`, `2019-intro`, `2019-snare-break-1`.

Vérifié page par page : la portée commence par une barre et enchaîne sur les
notes. **Ce n'est pas un défaut** — c'est la règle « ne jamais deviner une
métrique », qui est un pilier du projet. Les débloquer suppose de la changer.

Une piste défendable si on y touche : lire toutes les durées (elles ne
dépendent pas de la métrique), puis constater la somme que la majorité des
mesures atteint. C'est une mesure, pas une invention — mais le contrôle
arithmétique devient alors partiellement circulaire, et il faudrait le dire.

### A3 — Une famille de gravure inconnue, partagée · 3 séquences

`2004-battery-break`, `2004-feature`, `2009-drum-feature-5`.

Leurs polices portent trois noms mutilés différents (`TTFF55A818t00`,
`TTFE612310t00`…), mais leurs empreintes se recoupent : **28/40, 30/40,
15/17**. C'est **la même police ré-incorporée trois fois**. Une seule planche
de contact les nomme toutes les trois — c'est exactement le cas
BroadwayCopyist, qui avait rapporté huit partitions. **Meilleur rapport
effort/résultat du lot**, et probablement plus large que ces trois-là.

### A4 — Pas de hampes sur pages tracées · 2 séquences

`2019-closer-snare-break`, `2019-snare-break-2`. Leurs lignes de portée ne sont
**pas** remplies, donc le correctif des ligatures ne les concernait pas. Leurs
mesures sortent en `none` ou `spacing` : aucune hampe trouvée. Non diagnostiqué.

### A5 — La police Helsinki de Sibelius · 1 séquence

`2018-demonic-thesis`, 111 mesures, **401 empreintes à nommer**. Beaucoup
d'effort pour une seule partition ; à faire en dernier, ou jamais.

### A6 — Aucune portée trouvée · 3 séquences, trois causes distinctes

- `2017-movement-2-break` : ses filets ont bien **9 croisements symétriques**
  chacun, donc ce sont des portées à une ligne rejetées pour autre chose —
  probablement la borne `2 < interligne < 40` dans `_single_line`. **Sans
  doute une ligne.**
- `2016-feature-7` : **trois portées de batterie** (caisse claire, toms,
  basses) reliées par une même barre. Voir C2.
- `2016-snare-break-4` : 62 filets longs et **zéro** croisement symétrique.
  Non diagnostiqué.

### A7 — Durées qui ne bouclent pas · 4 séquences

`2010-keelan-s-solo`, `2011-movement-3-3`, `the-10-second-lick`,
`the-10-second-lick-simple`. Même méthode que M1, une mesure à la fois.

### A8 — Rythme illisible en BroadwayCopyist · 2 séquences

`faded`, `stainless-drum-set`. Le recalibrage des portées à une ligne en a
débloqué d'autres ; ces deux-là résistent encore.

---

## 5 · Dette et outillage

### C1 — Aucun test côté Python

Le pipeline n'a que la mesure de masse (`batch.py`) pour preuve. `text.py`
mérite mieux : les trois dialectes de tempo (`q = 168`, le clavier Sibelius
`q»¡§•`, `mm=180`) et l'établissement des lignes de base sont exactement le
genre de code qui casse en silence. L'ajout de pytest a été écarté en cours de
route pour ne pas introduire un outil de plus — **à trancher**.

### C2 — Les systèmes multi-portées ne sont gérés qu'à deux

La détection d'accolade repère une barre qui traverse deux portées et garde la
supérieure. Une partition de batterie complète (3 portées et plus) n'est pas
couverte — c'est ce qui bloque `2016-feature-7`.

### C3 — Tempo non lu sur les pages tracées

`Ghost Break` s'ouvre à 90 (le défaut de l'app) alors que la page imprime
♩ = 178. Sur une page convertie en contours, la marque métronomique est un
tracé, et `text.tempo` ne lit que les glyphes.

### C4 — **décision** : les tracés non appariés ne comptent pas comme inconnus

Affaiblissement assumé et documenté. Sur une page tracée, hampes, ligatures et
lignes de portée sont aussi des tracés, et rien ne distingue une tête de note
non reconnue d'une hampe. **Ces partitions ne sont donc contrôlées que par leur
arithmétique, pas par leur vocabulaire** — une garantie plus faible que le
reste du catalogue.

Piste pour resserrer : ne compter comme inconnue qu'une forme de **taille de
tête de note posée sur la portée**, ce qui exclut les hampes (rapport 0,12) et
les ligatures (rapport 12 à 22) sans rien inventer.

---

## 6 · Diffusion et présentation

### P1 — Revoir la taille des partitions retranscrites

L'intitulé porte deux lectures, et les deux ont de quoi être revues. À
préciser au moment de la prendre.

**Si c'est le poids des données** — 2,9 Mo pour 105 fichiers JSON, la plus
grosse à 96 Ko (`2019-closer-1`, 196 mesures). Elles sont toutes importées
d'un coup par `src/pieces/index.ts`, donc le paquet livré pèse **4,27 Mo**
avant compression. Aucune partition n'est chargée à la demande : ouvrir une
pièce de quinze mesures télécharge les cent cinq. Ça n'a jamais gêné en local ;
ça compte pour P2.

Pistes : import dynamique par pièce, ou un format plus serré — le JSON répète
`"duration"`, `"rest"`, `"accent"`, `"hand"` sur chacune des 42 261 frappes.

**Si c'est la taille à l'écran** — une ligne de portée occupe 140 px de haut
(30 au-dessus, 76 en dessous depuis que le sticking et les nuances s'y
empilent, plus la marge). Une pièce de 200 mesures fait donc plusieurs milliers
de pixels de haut, sans zoom ni densité réglable. Les repères ont été mesurés
sur le rendu, pas choisis : les revoir veut dire les re-mesurer.

### P2 — Publier en GitHub Page

L'app est un build Vite statique, donc techniquement c'est une action et un
fichier de workflow : chemin de base à configurer (`base` dans la config Vite,
le site vivant sous `/<dépôt>/`), un workflow `pages`, et le dépôt poussé — ce
qui est ton domaine.

Deux choses à regarder avant, et elles ne sont pas techniques :

- **Le poids.** 4,27 Mo de JavaScript à chaque visite (voir P1). Supportable,
  mais c'est le moment où ça cesse d'être gratuit.
- **Ce qu'on publie.** Jusqu'ici les transcriptions restent sur ta machine et
  le dépôt ne contient aucun PDF — c'est une règle écrite du projet. Publier
  met en ligne les *relevés dérivés* de transcriptions faites par d'autres, de
  spectacles sous droits. Chaque pièce porte l'URL dont elle vient et l'app
  l'affiche, ce qui est déjà le minimum honnête ; à toi de voir si ça suffit à
  ton usage. Ce n'est pas une objection, c'est un point à trancher en
  connaissance de cause.

### P3 — Créer un favicon

`apps/web/index.html` n'en déclare aucun : l'onglet affiche l'icône par
défaut. Petit, et visible dès P2.
