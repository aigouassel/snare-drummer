# Feuille de route

Ce qui reste à faire, et ce qu'on sait déjà de chaque chose. C'est une **liste**,
pas un plan : rien ici n'est ordonné par priorité et rien n'est engagé.

Chaque entrée porte les mesures déjà prises, pour qu'on puisse la reprendre
sans refaire le diagnostic. Les entrées marquées **décision** ne sont pas des
défauts à corriger : ce sont des choix à trancher, où le pipeline fait
aujourd'hui ce qu'on lui a demandé de faire.

> **Ce fichier est temporaire : à supprimer une fois tout traité.**
>
> Ce n'est pas de la coquetterie. Une feuille de route vidée de sa substance
> qui reste à la racine d'un dépôt devient un document qu'on croit à jour et
> qui ne l'est pas — exactement ce que `HELD-BACK.md` évite en étant généré.
> Ce qui mérite de survivre à une entrée traitée part dans le message de
> commit, dans le `README` ou dans `CLAUDE.md` ; le reste s'en va avec le
> fichier.

> État au 25 septembre 2026 : 110 des 128 séquences du répertoire sont
> jouables, 5 982 mesures dont 3 314 jouables (55,4 %). La proportion baisse
> pendant que le compte monte : cinq partitions sont entrées, et elles
> apportent plus de mesures qu'elles n'en font boucler. Le détail de ce qui
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

**1 193 mesures (19,9 %) dont les durées ne bouclent pas.** C'était 44,5 % en
début de parcours ; onze causes distinctes ont été trouvées et corrigées, aucune
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
| jouables | 3 314 (55,4 %) |
| **somme fausse** | **1 193 (19,9 %)** |
| que des silences (vérifiées, muettes) | 901 (15,1 %) |
| sans métrique | 343 (5,7 %) |
| vides | 126 (2,1 %) |
| lues à l'espacement | 53 (0,9 %) |
| symbole inconnu | 52 (0,9 %) |

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

## 4 · Les 18 séquences écartées

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

Depuis que les empreintes décrivent une forme, le même manque se voit sur des
partitions **publiées** : `training-day`, `2017-drum-break-finals` et
`2019-segment` sont tracées dans une famille qu'aucune table ne nomme, et
n'étaient lues que par des appariements marginaux — leurs têtes tombaient à
douze bits de *deux* familles à la fois, et laquelle gagnait tenait au compte.
`2019-segment` y a perdu 4 mesures et `2019-ghost-break` une. C'est une
planche de contact à faire, pas un seuil à desserrer : le mesurer a montré
qu'un seuil plus serré coûte ailleurs sans rien gagner ici (voir
`vocabulary.py`).

Leurs polices portent trois noms mutilés différents (`TTFF55A818t00`,
`TTFE612310t00`…), mais leurs empreintes se recoupent : **28/40, 30/40,
15/17**. C'est **la même police ré-incorporée trois fois**. Une seule planche
de contact les nomme toutes les trois — c'est exactement le cas
BroadwayCopyist, qui avait rapporté huit partitions. **Meilleur rapport
effort/résultat du lot**, et probablement plus large que ces trois-là.

### A5 — La police Helsinki de Sibelius · 1 séquence · *entrée, à peine*

`2018-demonic-thesis` est publiée depuis que les empreintes décrivent une
forme, mais **1 mesure sur 118** boucle. Les 401 empreintes restent à nommer
si on veut en faire une partition et pas une ligne au catalogue. Beaucoup
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

### A7 — Durées qui ne bouclent pas · 3 séquences

`2010-keelan-s-solo`, `2011-movement-3-3`, `the-10-second-lick-simple`. Même
méthode que M1, une mesure à la fois.

### A9 — Symboles non nommés · 1 séquence

`the-10-second-lick`. Elle était sous A7 ; ce n'est plus l'arithmétique qui la
bloque en premier mais son vocabulaire.

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

### C5 — Six entrées Opus perdues au report des empreintes

`digit.4`, `digit.7`, `digit.8`, `tremolo.slash`, `tremolo.wavy`,
`notehead.squareOpen`. Les étiquettes ont été reportées sur les empreintes
parcourues en retrouvant chaque entrée sur une page du corpus ; ces six-là
n'apparaissent sur aucune des 203 partitions téléchargées, donc sur aucune
qu'on sache remesurer. Elles ont été nommées sur un corpus plus large que
celui d'aujourd'hui. À reprendre en élargissant le corpus, ou à laisser : un
chiffrage Opus en 4, 7 ou 8 n'est plus lu.

---

## 6 · Présentation

### P1 — Revoir la taille des partitions retranscrites

L'intitulé porte deux lectures, et les deux ont de quoi être revues. À
préciser au moment de la prendre.

**Si c'est le poids des données** — 2,9 Mo pour 105 fichiers JSON, la plus
grosse à 96 Ko (`2019-closer-1`, 196 mesures). Elles sont toutes importées
d'un coup par `src/pieces/index.ts`, donc le paquet livré pèse **4,27 Mo**
avant compression. Aucune partition n'est chargée à la demande : ouvrir une
pièce de quinze mesures télécharge les cent cinq. Ça ne gênait pas en local ;
depuis que le site est publié, c'est ce que chaque visiteur télécharge.

Pistes : import dynamique par pièce, ou un format plus serré — le JSON répète
`"duration"`, `"rest"`, `"accent"`, `"hand"` sur chacune des 42 261 frappes.

**Si c'est la taille à l'écran** — une ligne de portée occupe 140 px de haut
(30 au-dessus, 76 en dessous depuis que le sticking et les nuances s'y
empilent, plus la marge). Une pièce de 200 mesures fait donc plusieurs milliers
de pixels de haut, sans zoom ni densité réglable. Les repères ont été mesurés
sur le rendu, pas choisis : les revoir veut dire les re-mesurer.
