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

> État au 25 septembre 2026 : 112 des 128 séquences du répertoire sont
> jouables, 6 026 mesures dont 3 320 jouables (55,1 %). La proportion baisse
> pendant que le compte monte : sept partitions sont entrées, et elles
> apportent plus de mesures qu'elles n'en font boucler. Une partition qu'on
> ne lisait pas du tout ne dégradait aucun taux. Le détail de ce qui
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

**1 227 mesures (20,4 %) dont les durées ne bouclent pas.** C'était 44,5 % en
début de parcours ; douze causes distinctes ont été trouvées et corrigées, aucune
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
| jouables | 3 320 (55,1 %) |
| **somme fausse** | **1 227 (20,4 %)** |
| que des silences (vérifiées, muettes) | 904 (15,0 %) |
| sans métrique | 343 (5,7 %) |
| vides | 126 (2,1 %) |
| lues à l'espacement | 53 (0,9 %) |
| symbole inconnu | 53 (0,9 %) |

Ces sept lignes comptent les mesures **livrées**, comme `bars_total` dans
`batch.py`, qui n'incrémente qu'après le `continue` écartant une pièce sans
rien de jouable. Le même décompte étendu aux seize séquences écartées donne
6 246 mesures — juste aussi, et d'un autre nom.

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

## 4 · Les 16 séquences écartées

### A2 — Aucun chiffrage lu · les portées par bouts sont réglées, deux vrais cas restent

L'entrée disait « aucun chiffrage imprimé » et se croyait une décision. Relevé
page par page, **quatre de ces six partitions impriment bel et bien leur
chiffrage** ; seules `2019-intro` et `2019-snare-break-1` commencent par une
clé puis directement les notes.

La cause des portées tracées par bouts est **réparée** (`layout._stitch`,
`rhythm._staff_line_edges`, `layout._barlines_among`). Elle valait bien plus
que le chiffrage, et bien plus que ces trois partitions : **53 des 203
partitions tenues localement, un quart du corpus, gravent leurs filets mesure
par mesure**. Sur le répertoire entier, 112 séquences passent à 116 et 3 320
mesures jouables à 3 410, sans qu'aucune pièce ne perde une seule mesure
jouable.

`2017-opening-snare-break` était donné pour un quatrième cas, « une page
tracée dont les chiffres ne sont pas dans `drawn.json` ». C'était faux deux
fois : relevée forme par forme, la page n'a **rien** qu'aucune table ne nomme —
son 4 de chiffrage est à 1 bit de celui de MScore, ses têtes, sa clé, ses
crochets et ses accents à 0 — et elle est aujourd'hui livrée, 9 mesures, aucune
sans métrique et aucun symbole non nommé. C'était le défaut de portée, seul.

Ce qui a rendu ces pages lisibles, et qui mérite de survivre à cette entrée :

- le recollement se pose sur l'about, pas sur le chevauchement. Mesuré sur les
  203 partitions, 4 373 paires de filets colinéaires se touchent à 0,2 point
  près et la paire non jointive la plus proche est à 2,55 points ; il n'y a
  rien entre les deux. Fusionner deux portées voisines est donc hors de
  portée du seuil.
- `rhythm.py` devait suivre et personne ne l'avait vu. Sur une page convertie
  en contours, un filet de portée n'est distingué d'une ligature que par son
  identité — il court d'un bout à l'autre de sa portée. Une portée recollée
  dont les segments ne le sont pas ne correspond plus à aucun de ses bouts :
  `2017-drum-break-finals` s'est lue huit fois trop vite, et sans erreur.
- la « double barre initiale » du relevé ci-dessus était une **clé de
  percussion**. Deux traits épais, quatre filets, un interligne de haut.

Reste `2014-solo-1`, que ne lit aucun vocabulaire — voir A3.

**Pour les deux vrais cas — `2019-intro` et `2019-snare-break-1` — ne pas
déduire la métrique.** La piste « prendre la
somme que la majorité des mesures atteint » a été mesurée en aveugle sur 117
séquences dont la métrique est imprimée et connue : elle se trompe sur
**18,8 % des pièces et 26,9 % des mesures**, et ferait déclarer jouables 70
mesures que leur page dément. `2011-movement-3-3` en donne la raison : son
mode rassemble 67 % des mesures — plus net que celui de `2019-intro` — et il
est faux. La netteté du pic ne distingue pas une métrique réelle d'un biais de
lecture uniforme, donc aucun seuil ne sauve la piste. S'ajoute qu'un total en
temps ne désigne pas une métrique : six temps, c'est 6/4 dans 150 mesures du
catalogue, 3/2 dans 106 et 12/8 dans 57.

Ce que la déduction ferait perdre est exactement ce que ce dépôt craint. Le
contrôle arithmétique garderait son pouvoir sur l'erreur locale et le perdrait
entièrement sur l'**erreur uniforme** : un pipeline lisant toutes les durées de
moitié produirait un mode de 2, en déduirait 2/4, et boucleraient à 100 %. Les
douze pannes listées dans `CLAUDE.md` sont toutes de cette famille-là. Et
`batch.py` cesserait de mesurer l'accord avec la page pour mesurer l'accord des
mesures entre elles, sans plus pouvoir descendre sous la part du mode.

La seule forme tenable, si on y tient : **déclarer** la métrique à la main pour
ces deux séquences, dans un fichier à côté de `pipeline/vocabulary/` — pas dans
`catalogue.json`, qui est scrapé et serait écrasé. C'est la concession déjà
faite à `label.py`, elle est auditable et par séquence, et surtout elle laisse
le contrôle arithmétique **extérieur** : la métrique vient d'un œil, pas des
durées qu'elle vérifie.

### A3 — ~~Une famille de gravure tracée que personne n'a nommée~~ · réglée

La famille s'appelle **Ash** et sa table est `pipeline/vocabulary/ash.json`.
Le nom est lu dans les fichiers : ces pages n'embarquent aucune police
musicale — leur musique n'arrive qu'en courbes — mais bien leur police de
texte, qui s'appelle `ashtext`.

Son étendue est de **douze partitions** du corpus, pas les trois que l'entrée
visait, et elles sont imprimées par quatre chaînes différentes (jsPDF, PDFium,
Quartz, Print To PDF) : c'est le contour qui les réunit, pas le producteur.
Mesuré à mesures jouables, sur les neuf qui bougent :

| | avant | après |
| --- | --- | --- |
| `training-day` *(publiée)* | écartée, 0/28 | 14/28 |
| `2017-drum-break-finals` *(publiée)* | 20/57 | 31/57 |
| `2019-segment` *(publiée)* | 3/30 | 10/30 |
| `2019-ghost-break` | 16/42 | 26/42 |
| `2019-opener-13` | 26/54 | 38/54 |
| `2017-movement-2` | 22/81 | 27/81 |
| `2018-snare-feature-1` | 9/24 | 13/24 |
| `2019-closer-6` | 10/18 | 13/18 |
| `2018-snare-feature` | 3/9 | 6/9 |

Échantillon de 80 : 1 777 → 1 802 mesures jouables, deux pièces changées, dans
le bon sens toutes les deux.

Ce qui reste sans nom dans cette famille l'est exprès, et c'est l'entrée C4
qui le dit : un trait oblique fin de 3,8 × 4,5 points, vu 195 fois sur neuf
partitions, peut être la barre d'une note d'agrément, une barre de roulement
dessinée fine ou la moitié d'une croix. Le nommer compterait peut-être deux
frappes là où la page en imprime une.

`2004-feature`, qui résistait encore : sa police de têtes n'en contient que
trois et passe donc par `corroborate`, qui exige l'unanimité. Deux de ses trois
formes étaient à zéro bit de Maestro, la troisième est un triangle pointe en
bas que la table ne portait pas sous ce dessin-là, et toute la police tombait
avec elle. Écartée (0/20) → **14/20**.

`2014-solo-1` n'est pas une affaire de vocabulaire. Sa gravure manuscrite
n'existe que là : sa tête de note, cherchée sur les 203 PDF du corpus, ne se
retrouve dans aucun autre. Et nommer ne l'aiderait pas — l'essai a été fait,
avec une table de neuf formes qui nomme ses têtes, ses lettres et sa clé : la
page rend toujours **une** mesure, vide, alors qu'elle en imprime une douzaine.
Ses six voisines de A2 sont dans le même cas. C'est la mise en page qu'il faut
regarder, pas la table.

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
