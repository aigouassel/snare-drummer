# Ce qui n’est pas retranscrit

69 des 128 séquences du répertoire sont jouables dans l’application. Voici les 59 autres, et pourquoi.

> Généré par `pipeline/run/held.py`, à partir de la lecture que le pipeline fait aujourd’hui. Une liste écrite à la main deviendrait fausse dès que quelque chose se met à marcher.

La raison donnée est celle qui bloque **le plus grand nombre de mesures** de la séquence, sauf un chiffre de n-olet non rattaché, qui écarte à lui seul ; le détail par mesure suit chaque entrée. Une séquence n’est publiée que si assez de ses mesures bouclent exactement *et* contiennent une frappe — la part est `batch.FLOOR` — et si aucun chiffre de n-olet n’y est resté sans ses notes.

## Aucun chiffrage de mesure n'a été lu — 2 séquences

Le pipeline ne devine jamais une métrique. Ces partitions n'en impriment pas au début, ou l'impriment dans une fonte qu'aucun vocabulaire ne nomme — et sans métrique, une mesure n'a rien contre quoi boucler.

- **Santa Clara Vanguard (SCV) 2019 — Intro** (`2019-intro`)  
  47 mesures lues : 47 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Intro.pdf)
- **Santa Clara Vanguard (SCV) 2019 — Snare Break** (`2019-snare-break-1`)  
  9 mesures lues : 9 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Break-1.pdf)

## Le rythme n'a pas pu être lu dans la notation — 1 séquence

Les notes sont là, mais leurs hampes ou leurs ligatures ne se laissent pas mesurer, donc la mesure retombe sur l'espacement — une lecture trop faible pour être publiée.

- **BYOS — Stainless Drum Set** (`stainless-drum-set`)  
  33 mesures lues : 15 espacement, 5 inconnu, 5 somme, 5 polyphonie, 3 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/Stainless-Drum-Set.pdf)

## Un chiffre de n-olet n'a pas pu être rattaché à ses notes — 50 séquences

Un chiffre compte des subdivisions, pas des têtes de note, et `rhythm.tuplet_groups` cherche autant de notes que le chiffre le dit — vrai d'un groupe homogène, faux dès que les valeurs se mélangent. Ces groupes portent un crochet, qui énonce l'étendue ; le lire est inscrit dans ROADMAP.md. D'ici là, décision prise en connaissance du coût : une partition qui laisse un chiffre non lu n'est pas livrée, même si le reste de ses mesures boucle.

- **Atlanta Quest 2019 — Snare Break** (`2019-snare-break-2`) · musique tracée en courbes  
  12 mesures lues : 6 silences, 4 somme, 1 métrique, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Break-2.pdf)
- **Ayala HS 2018 — Opener (Fall Season)** (`2018-opener-fall-season`)  
  81 mesures lues : 69 silences, 6 somme, 6 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Opener-Fall-Season.pdf)
- **BYOS — Faded** (`faded`)  
  26 mesures lues : 13 espacement, 6 polyphonie, 5 inconnu, 1 n-olet, 1 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/Faded.pdf)
- **BYOS — Firemen** (`firemen`)  
  17 mesures lues : 6 espacement, 3 inconnu, 3 somme, 2 n-olet, 2 silences, 1 polyphonie  
  [source](https://lothype.com/wp-content/uploads/2020/01/Firemen.pdf)
- **BYOS — Stainless Snare** (`stainless-snare`)  
  47 mesures lues : 13 inconnu, 11 polyphonie, 10 espacement, 6 silences, 3 vide, 2 somme, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/Stainless-Snare.pdf)
- **Blue Devils B 2017 — Snare Break** (`2017-snare-break`) · musique tracée en courbes  
  9 mesures lues : 5 somme, 3 silences, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Snare-Break.pdf)
- **Blue Knights 2019 — Movement 2** (`2019-movement-2-1`)  
  146 mesures lues : 128 silences, 10 somme, 7 n-olet, 1 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-2-1.pdf)
- **Blue Knights 2019 — Movement 4** (`2019-movement-4-1`)  
  147 mesures lues : 115 silences, 18 somme, 12 vide, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-4-1.pdf)
- **Bluecoats 2019 — Movement 2** (`2019-movement-2-2`)  
  148 mesures lues : 109 silences, 22 somme, 14 métrique, 3 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-2-2.pdf)
- **Bluecoats 2019 — Opener** (`2019-opener-2`)  
  33 mesures lues : 26 métrique, 5 silences, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Opener-2.pdf)
- **Boston Crusaders 2019 — Drum Break (as of (7-26-19)** (`2019-drum-break-as-of-7-26-19`)  
  162 mesures lues : 81 silences, 68 métrique, 12 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Drum-Break-as-of-7-26-19.pdf)
- **Broken City 2019 — Movement 2** (`2019-movement-2-10`)  
  51 mesures lues : 32 silences, 13 somme, 4 n-olet, 2 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-2-10.pdf)
- **Cadets 2018 — Demonic Thesis** (`2018-demonic-thesis`) · musique tracée en courbes  
  118 mesures lues : 52 silences, 45 vide, 18 somme, 2 n-olet, 1 polyphonie  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-_Demonic-Thesis_.pdf)
- **Carolina Crown 2019 — Closer** (`2019-closer-1`)  
  196 mesures lues : 151 silences, 36 somme, 5 métrique, 3 polyphonie, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Closer-1.pdf)
- **Carolina Crown 2019 — Movement 2** (`2019-movement-2-3`)  
  168 mesures lues : 141 silences, 23 somme, 4 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-2-3.pdf)
- **Carolina Crown 2019 — Opener** (`2019-opener-3`)  
  90 mesures lues : 61 silences, 16 somme, 8 n-olet, 5 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Opener-3.pdf)
- **Cavaliers Indoor Percussion 2017 — Opener** (`2017-opener-13`)  
  31 mesures lues : 16 silences, 12 somme, 2 vide, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Opener-13.pdf)
- **Center Grove HS 2017 — Movement 3** (`2017-movement-3-5`)  
  59 mesures lues : 44 silences, 8 somme, 4 espacement, 2 vide, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Movement-3-5.pdf)
- **Freelancers 2010 — Segment** (`2010-segment-6`)  
  35 mesures lues : 25 silences, 8 somme, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2010-Segment-6.pdf)
- **Gateway 2017 — Feature** (`2017-feature`)  
  19 mesures lues : 14 silences, 4 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Feature.pdf)
- **Glassmen 2018 — Movement 2** (`2018-movement-2-4`)  
  126 mesures lues : 115 silences, 6 n-olet, 5 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Movement-2-4.pdf)
- **Infinity 2016 — Closer** (`2016-closer-7`)  
  89 mesures lues : 41 silences, 18 somme, 12 inconnu, 8 polyphonie, 4 vide, 4 n-olet, 2 espacement  
  [source](https://lothype.com/wp-content/uploads/2020/01/2016-Closer-7.pdf)
- **Infinity 2016 — Movement 2** (`2016-movement-2-9`)  
  40 mesures lues : 20 silences, 7 somme, 6 polyphonie, 3 inconnu, 2 vide, 1 espacement, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2016-Movement-2-9.pdf)
- **Infinity 2016 — Opener** (`2016-opener-13`)  
  26 mesures lues : 8 somme, 7 silences, 5 polyphonie, 2 inconnu, 2 n-olet, 1 vide, 1 espacement  
  [source](https://lothype.com/wp-content/uploads/2020/01/2016-Opener-13.pdf)
- **Infinity 2 2018 — Snare Break** (`2018-snare-break-5`)  
  16 mesures lues : 13 silences, 2 n-olet, 1 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Snare-Break-5.pdf)
- **Jersey Surf 2018 — Movement 2** (`2018-movement-2-5`)  
  126 mesures lues : 115 silences, 6 n-olet, 5 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Movement-2-5.pdf)
- **Keelan Tobia — The 10 Second Lick (Simple)** (`the-10-second-lick-simple`)  
  6 mesures lues : 2 somme, 2 vide, 1 espacement, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/The-10-Second-Lick-Simple.pdf)
- **Madison Scouts 2018 — Racing Heart** (`2018-racing-heart`)  
  80 mesures lues : 48 silences, 17 somme, 13 vide, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-_Racing-Heart_.pdf)
- **Music City 2018 — Opener** (`2018-opener-5`)  
  85 mesures lues : 38 silences, 27 somme, 12 polyphonie, 6 n-olet, 1 inconnu, 1 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Opener-5.pdf)
- **Pacific Crest 2018 — Drum Feature** (`2018-drum-feature`)  
  54 mesures lues : 43 silences, 10 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Drum-Feature.pdf)
- **Pacific Crest 2018 — Movement 2** (`2018-movement-2-7`)  
  11 mesures lues : 9 silences, 1 n-olet, 1 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Movement-2-7.pdf)
- **Pulse 2019 — Snare Break (Early Season)** (`2019-snare-break-early-season-2`) · musique tracée en courbes  
  22 mesures lues : 12 silences, 9 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Break-Early-Season-2.pdf)
- **Pulse 2019 — Snare Solo** (`2019-snare-solo`)  
  16 mesures lues : 14 silences, 1 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Solo.pdf)
- **RCC 2019 — Snare Break (Early Season)** (`2019-snare-break-early-season-3`)  
  24 mesures lues : 20 silences, 3 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Break-Early-Season-3.pdf)
- **Ralph Nader — Let The Groove Get In** (`let-the-groove-get-in`)  
  17 mesures lues : 12 silences, 4 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/Let-The-Groove-Get-In.pdf)
- **Rhythm X 2019 — Full Show** (`2019-full-show`)  
  143 mesures lues : 109 silences, 26 somme, 3 vide, 2 n-olet, 2 polyphonie, 1 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Full-Show.pdf)
- **Rhythm X 2019 — Movement 3** (`2019-movement-3-3`)  
  19 mesures lues : 15 silences, 2 somme, 1 métrique, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-3-3.pdf)
- **Rhythm X 2019 — Movement 5** (`2019-movement-5`)  
  31 mesures lues : 18 silences, 11 somme, 1 n-olet, 1 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-5.pdf)
- **SCVC 2017 — Snare Break** (`2017-snare-break-2`)  
  21 mesures lues : 8 polyphonie, 7 silences, 4 somme, 1 inconnu, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Snare-Break-2.pdf)
- **Santa Clara Vanguard (SCV) 2019 — Closer (as of 7-31-19)** (`2019-closer-as-of-7-31-19`)  
  76 mesures lues : 57 silences, 17 somme, 1 métrique, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Closer-as-of-7-31-19.pdf)
- **Santa Clara Vanguard (SCV) 2019 — Movement 2** (`2019-movement-2-4`)  
  140 mesures lues : 120 silences, 17 somme, 2 métrique, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Movement-2-4.pdf)
- **Santa Clara Vanguard (SCV) 2019 — Opener** (`2019-opener-5`)  
  97 mesures lues : 71 silences, 13 somme, 9 métrique, 2 polyphonie, 2 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Opener-5.pdf)
- **Spirit of Atlanta 2019 — Opener** (`2019-opener-7`)  
  58 mesures lues : 45 métrique, 12 silences, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Opener-7.pdf)
- **Stryke 2018 — Opening Snare Feature** (`2018-opening-snare-feature`)  
  36 mesures lues : 33 silences, 2 somme, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Opening-Snare-Feature.pdf)
- **Teal Sound 2011 — Movement 2** (`2011-movement-2-3`)  
  43 mesures lues : 33 silences, 5 somme, 4 vide, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2011-Movement-2-3.pdf)
- **United Percussion 2019 — Segment** (`2019-segment`) · musique tracée en courbes  
  30 mesures lues : 16 somme, 9 silences, 5 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Segment.pdf)
- **Unity 2017 — Excerpt (Finals)** (`2017-excerpt-finals`)  
  19 mesures lues : 18 silences, 1 n-olet  
  [source](https://lothype.com/wp-content/uploads/2020/01/2017-Excerpt-Finals.pdf)
- **Vessel 2019 — Snare Feature** (`2019-snare-feature`)  
  18 mesures lues : 9 silences, 6 n-olet, 3 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Feature.pdf)
- **Vigilantes 2018 — Feature** (`2018-feature`)  
  19 mesures lues : 14 silences, 3 n-olet, 2 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Feature.pdf)
- **Vigilantes 2018 — Feature(1)** (`2018-feature1`)  
  19 mesures lues : 13 silences, 3 n-olet, 3 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2018-Feature1.pdf)

## Des symboles n'ont pas pu être nommés — 1 séquence

Une forme sans étiquette rend sa mesure suspecte plutôt que d'être rapprochée de la plus proche, ce qui est la règle du projet.

- **Keelan Tobia — The 10 Second Lick** (`the-10-second-lick`)  
  3 mesures lues : 2 inconnu, 1 polyphonie  
  [source](https://lothype.com/wp-content/uploads/2020/01/The-10-Second-Lick.pdf)

## Les durées ne bouclent pas — 2 séquences

Tout est lu, mais la somme d'une mesure ne fait pas sa métrique. Parfois c'est la lecture qui se trompe ; parfois c'est la source, qui est un relevé fait à l'oreille et se trompe aussi.

- **Freelancers 2010 — Keelan_s Solo** (`2010-keelan-s-solo`)  
  4 mesures lues : 4 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2010-Keelan_s-Solo.pdf)
- **Teal Sound 2011 — Movement 3** (`2011-movement-3-3`)  
  23 mesures lues : 18 somme, 5 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/2011-Movement-3-3.pdf)

## Aucune portée n'a été trouvée — 3 séquences

Ni portée ni barre de mesure : soit la page dessine ses lignes d'une façon que layout.py ne reconnaît pas, soit elle porte plusieurs portées d'instruments différents reliées par une même barre.

- **Cadets Winter Percussion 2016 — Feature** (`2016-feature-7`)  
  0 mesure lue  
  [source](https://lothype.com/wp-content/uploads/2020/01/2016-Feature-7.pdf)
- **Dartmouth HS 2014 — Solo** (`2014-solo-1`)  
  0 mesure lue  
  [source](https://lothype.com/wp-content/uploads/2020/01/2014-Solo-1.pdf)
- **Matrix 2016 — Snare Break** (`2016-snare-break-4`) · musique tracée en courbes  
  0 mesure lue  
  [source](https://lothype.com/wp-content/uploads/2020/01/2016-Snare-Break-4.pdf)

