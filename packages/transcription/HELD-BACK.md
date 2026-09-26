# Ce qui n’est pas retranscrit

117 des 128 séquences du répertoire sont jouables dans l’application. Voici les 11 autres, et pourquoi.

> Généré par `pipeline/held.py`, à partir de la lecture que le pipeline fait aujourd’hui. Une liste écrite à la main deviendrait fausse dès que quelque chose se met à marcher.

La raison donnée est celle qui bloque **le plus grand nombre de mesures** de la séquence ; le détail par mesure suit chaque entrée. Une séquence n’est publiée que si au moins une de ses mesures boucle exactement *et* contient une frappe.

## Aucun chiffrage de mesure n'a été lu — 2 séquences

Le pipeline ne devine jamais une métrique. Ces partitions n'en impriment pas au début, ou l'impriment dans une fonte qu'aucun vocabulaire ne nomme — et sans métrique, une mesure n'a rien contre quoi boucler.

- **Santa Clara Vanguard (SCV) 2019 — Intro** (`2019-intro`)  
  47 mesures lues : 47 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Intro.pdf)
- **Santa Clara Vanguard (SCV) 2019 — Snare Break** (`2019-snare-break-1`)  
  9 mesures lues : 9 métrique  
  [source](https://lothype.com/wp-content/uploads/2020/01/2019-Snare-Break-1.pdf)

## Le rythme n'a pas pu être lu dans la notation — 2 séquences

Les notes sont là, mais leurs hampes ou leurs ligatures ne se laissent pas mesurer, donc la mesure retombe sur l'espacement — une lecture trop faible pour être publiée.

- **BYOS — Faded** (`faded`)  
  26 mesures lues : 14 espacement, 7 somme, 5 inconnu  
  [source](https://lothype.com/wp-content/uploads/2020/01/Faded.pdf)
- **BYOS — Stainless Drum Set** (`stainless-drum-set`)  
  33 mesures lues : 20 espacement, 5 inconnu, 5 somme, 3 vide  
  [source](https://lothype.com/wp-content/uploads/2020/01/Stainless-Drum-Set.pdf)

## Des symboles n'ont pas pu être nommés — 1 séquence

Une forme sans étiquette rend sa mesure suspecte plutôt que d'être rapprochée de la plus proche, ce qui est la règle du projet.

- **Keelan Tobia — The 10 Second Lick** (`the-10-second-lick`)  
  3 mesures lues : 2 inconnu, 1 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/The-10-Second-Lick.pdf)

## Les durées ne bouclent pas — 3 séquences

Tout est lu, mais la somme d'une mesure ne fait pas sa métrique. Parfois c'est la lecture qui se trompe ; parfois c'est la source, qui est un relevé fait à l'oreille et se trompe aussi.

- **Freelancers 2010 — Keelan_s Solo** (`2010-keelan-s-solo`)  
  4 mesures lues : 4 somme  
  [source](https://lothype.com/wp-content/uploads/2020/01/2010-Keelan_s-Solo.pdf)
- **Keelan Tobia — The 10 Second Lick (Simple)** (`the-10-second-lick-simple`)  
  6 mesures lues : 3 somme, 2 vide, 1 espacement  
  [source](https://lothype.com/wp-content/uploads/2020/01/The-10-Second-Lick-Simple.pdf)
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

