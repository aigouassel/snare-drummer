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

> État au 26 septembre 2026 : **68 des 128 séquences** du répertoire sont
> jouables, 3 174 mesures dont 2 157 jouables (68,0 %). C'était 116 séquences
> et 3 672 mesures jouables le matin même : 48 séquences ont été écartées
> parce qu'un chiffre de n-olet y reste sans ses notes, décision prise avec le
> coût en vue — 1 515 mesures jouables retirées pour 110 mesures fautives. Le
> taux monte parce que le dénominateur part avec elles, pas parce que la
> lecture s'est améliorée ; ce qui l'a améliorée, c'est la lecture des barres
> de trémolo comme les roulements qu'elles sont (+177 mesures). Le détail de ce qui
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

**391 mesures (12,3 %) dont les durées ne bouclent pas**, sur les 68
séquences livrées. C'était 44,5 % en
début de parcours ; seize causes distinctes ont été trouvées et corrigées,
aucune deux fois la même. Ce qui reste est une longue traîne sans coupable unique.

Ce qui a été mesuré en cherchant la seizième, et qui évite de refaire le
diagnostic : l'écart `lu − attendu` en noires est un bien meilleur instrument
que le rapport, qui mélange les métriques — une croche manquante vaut 15/16 en
4/4 et 7/8 en 2/4, donc une cause apparaît sous deux nombres. Le taux par
famille de gravure est ce qui a désigné le coupable : 9,8 % des mesures Bravura
contre 0,2 % des Opus, un facteur 40 qui ne peut pas être du bruit. Trois
hypothèses ont été écartées par la mesure avant la bonne — barre de mesure
manquée (les mesures fautives ne sont pas plus larges), ligatures tracées au
lieu d'être remplies (une seule partition sur 203), fioritures mal classées
(MuseScore les grave à 0,700 de la taille pleine, Opus à 0,602, les deux du bon
côté du seuil).

Une troisième cause est **diagnostiquée, pas corrigée, et tranchée** : les
séquences qui la portent ne sont plus livrées. Le diagnostic vaut d'être
gardé : `rhythm.tuplet_groups` cherche exactement `count` onsets
consécutifs sous un chiffre de n-olet. Or un chiffre compte des **subdivisions,
pas des têtes de note** — « 9 » veut dire neuf unités dans le temps de huit, et
si le groupe mélange les valeurs, le nombre de têtes n'a plus rien à voir avec
le chiffre. L'illusion tient à ce que la plupart des groupes sont homogènes.
Mesuré : 123 mesures échouent avec au moins un chiffre lâché, dont 54 pour
« 3 demandées, 2 restantes ».

La page dit pourtant l'étendue quand elle trace un **crochet**, ce qui est le
cas de ces groupes-là : le crochet énonce ce que rien d'autre n'énonce.
`CLAUDE.md` a raison de dire que la plupart des n-olets ligaturés n'en portent
pas — mais ceux qui échouent en portent. Lire le crochet est une capacité
nouvelle dans `ink`, pas une réparation, d'où son inscription ici.

**Décision** : plutôt que de nommer le refus mesure par mesure, comme pour les
divisi, toute séquence contenant un chiffre non rattaché est écartée entière.
La mesure porte `droppedTuplets`, `batch.py` retient la séquence, et
`HELD-BACK.md` la liste sous sa raison. Le coût, mesuré avant de décider : 48
séquences sur 116 et 1 515 mesures jouables sur 3 672, pour 110 mesures
fautives — la plupart de ces séquences n'en portaient qu'une. Lire les crochets
rend tout cela d'un coup, ce qui fait de cette entrée la plus rentable de la
liste.

Une deuxième cause a été identifiée et **écartée du compte plutôt que corrigée** :
69 mesures sont des divisi, deux parties écrites sur une même portée, l'une
hampes en l'air et l'autre hampes en bas. Leurs durées ne sont pas fausses ; le
modèle ne sait pas tenir deux voix dans une mesure, alors les deux sont lues
dans le même flux et la somme double. Elles portent maintenant
`readFrom: 'polyphonic'` et sortent de M1, où elles auraient envoyé quelqu'un
réparer ce qui n'est pas cassé. Les rendre jouables demanderait deux voix dans
`packages/core`, le lecteur et l'affichage : c'est une fonctionnalité, pas une
réparation, et elle n'est pas engagée.

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
| jouables | 2 157 (68,0 %) |
| **somme fausse** | **391 (12,3 %)** |
| que des silences (vérifiées, muettes) | 385 (12,1 %) |
| sans métrique | 136 (4,3 %) |
| lues à l'espacement | 50 (1,6 %) |
| vides | 35 (1,1 %) |
| symbole inconnu | 15 (0,5 %) |
| deux voix sur la portée | 5 (0,2 %) |

Ces huit lignes comptent les mesures **livrées**, comme `bars_total` dans
`run/batch.py`, qui n'incrémente qu'après le `continue` écartant une pièce sans
rien de jouable. Le même décompte étendu aux soixante séquences écartées donne
un autre total, juste aussi et portant le même nom.

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

## 4 · Les 60 séquences écartées

### A2 — Aucun chiffrage imprimé · 2 séquences · **tranché : elles restent dehors**

`2019-intro` (47 mesures) et `2019-snare-break-1` (9). Ces deux-là impriment
vraiment une clé puis les notes, sans chiffrage. Les déduire a été mesuré et
écarté — la mesure est dans `CLAUDE.md`, sous les choix assumés, pour qu'on ne
la repropose pas. Les débloquer voudrait dire déclarer leur métrique à l'œil,
et on a choisi de ne pas ouvrir ce fichier pour deux partitions. Rien à faire
ici : l'entrée ne survit que pour dire que c'est réglé, et part avec le
fichier.

### A5 — La police Helsinki de Sibelius · 1 séquence · **tranché : on ne la fera pas**

`2018-demonic-thesis`, 118 mesures dont **une** bouclait. Elle a été publiée un
temps, sur la règle d'alors — une mesure jouable suffisait — ce qui en faisait
une entrée de catalogue avec une portée dessinée dessous. Le plancher de
livraison l'a écartée, et `HELD-BACK.md` en donne la raison mesurée : 52 de ses
mesures ne contiennent que des silences.

La rouvrir voudrait dire nommer **401 empreintes** à l'œil pour une seule
partition. C'est décidé : on ne le fera pas. L'entrée ne survit que pour dire
que ce n'est pas un oubli.

### A6 — Aucune portée trouvée · 3 séquences, trois causes distinctes

`2017-movement-2-break` en est sortie : le recollement des filets l'a rendue
lisible, 5 mesures jouables sur 21.

- `2016-feature-7` : **trois portées de batterie** (caisse claire, toms,
  basses) reliées par une même barre. Voir C2.
- `2016-snare-break-4` : 62 filets longs et **zéro** croisement symétrique.
  Non diagnostiqué.
- `2014-solo-1` : gravure manuscrite qui n'existe nulle part ailleurs — sa tête
  de note, cherchée sur les 203 partitions du corpus, ne se retrouve dans
  aucune autre. Ce n'est pas la table qui la bloque : l'essai a été fait, avec
  neuf formes nommant ses têtes, ses lettres et sa clé, et la page rend
  toujours **une** mesure, vide, là où elle en imprime une douzaine.

### A7 — Durées qui ne bouclent pas · 3 séquences

`2010-keelan-s-solo`, `2011-movement-3-3`, `the-10-second-lick-simple`. Même
méthode que M1, une mesure à la fois.

### A8 — Rythme illisible en BroadwayCopyist · 2 séquences

`faded`, `stainless-drum-set`. Le recalibrage des portées à une ligne en a
débloqué d'autres ; ces deux-là résistent encore.

---

### A9 — Symboles non nommés · 1 séquence

`the-10-second-lick`. Elle était sous A7 ; ce n'est plus l'arithmétique qui la
bloque en premier mais son vocabulaire.

## 5 · Dette et outillage

### C1 — Aucun test côté Python

Le pipeline n'a que la mesure de masse (`run/batch.py`) pour preuve. `text.py`
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
