#!/usr/bin/env python3
"""
Write down which sequences of the repertoire are not shipped, and why.

Generated rather than written, and that is the point: a hand-written list of
what does not work goes stale the moment something starts working, and then
quietly misleads. This one is produced from the pipeline's own reading, so it
is wrong only when the pipeline is.

    .venv/bin/python held.py            # -> ../HELD-BACK.md
"""
import collections
import os
import sys
from fractions import Fraction

import batch
import ink
import transcribe

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'HELD-BACK.md')

# The reasons a bar can fail, most specific first: a bar with no metre cannot
# be judged on anything else, a bar with nothing in it has no durations to
# add up, and so on down to a sum that does not close.
REASONS = [
    ('métrique', "aucun chiffrage de mesure n'a été lu",
     "Le pipeline ne devine jamais une métrique. Ces partitions n'en "
     "impriment pas au début, ou l'impriment dans une fonte qu'aucun "
     "vocabulaire ne nomme — et sans métrique, une mesure n'a rien contre "
     "quoi boucler."),
    ('vide', "les notes n'ont pas été lues",
     "Les portées et les barres sont trouvées, mais rien de rythmique ne "
     "l'est. En général une police de gravure que personne n'a nommée : une "
     "famille inconnue reste invisible, puisque l'attribution par forme ne "
     "compare qu'aux vocabulaires existants."),
    ('espacement', "le rythme n'a pas pu être lu dans la notation",
     "Les notes sont là, mais leurs hampes ou leurs ligatures ne se "
     "laissent pas mesurer, donc la mesure retombe sur l'espacement — une "
     "lecture trop faible pour être publiée."),
    ('inconnu', "des symboles n'ont pas pu être nommés",
     "Une forme sans étiquette rend sa mesure suspecte plutôt que d'être "
     "rapprochée de la plus proche, ce qui est la règle du projet."),
    ('somme', "les durées ne bouclent pas",
     "Tout est lu, mais la somme d'une mesure ne fait pas sa métrique. "
     "Parfois c'est la lecture qui se trompe ; parfois c'est la source, qui "
     "est un relevé fait à l'oreille et se trompe aussi."),
    ('silences', "rien que des silences",
     "La partition est vérifiable et muette : il n'y a rien à travailler."),
    ('aucune', "aucune portée n'a été trouvée",
     "Ni portée ni barre de mesure : soit la page dessine ses lignes d'une "
     "façon que layout.py ne reconnaît pas, soit elle porte plusieurs "
     "portées d'instruments différents reliées par une même barre."),
]


def survey():
    _data, entries = batch.sequences(repertoire=True)
    shipped = {name[:-5] for name in os.listdir(batch.PIECES)
               if name.endswith('.json')}
    rows = []
    for entry in entries:
        if entry['id'] in shipped:
            continue
        path = os.path.join(batch.CORPUS, entry['id'] + '.pdf')
        if not os.path.exists(path):
            rows.append({**entry, 'reason': 'aucune', 'bars': 0,
                         'drawn': 0, 'counts': {}})
            continue
        piece = transcribe.transcribe(path, entry)
        counts = collections.Counter()
        for bar in piece['bars']:
            if bar['meter'] is None:
                counts['métrique'] += 1
            elif not bar['events']:
                counts['vide'] += 1
            elif bar['unnamedSymbols']:
                counts['inconnu'] += 1
            elif bar['readFrom'] != 'notation':
                counts['espacement'] += 1
            else:
                played = sum(Fraction(*e['duration']) for e in bar['events'])
                whole = Fraction(bar['meter'][0] * 4, bar['meter'][1])
                counts['silences' if played == whole else 'somme'] += 1
        reason = 'aucune' if not piece['bars'] else max(
            counts.items(), key=lambda kv: kv[1])[0]
        rows.append({**entry, 'reason': reason, 'bars': len(piece['bars']),
                     'drawn': piece['extraction'].get('pagesDrawn', 0),
                     'counts': dict(counts.most_common())})
    return rows, len(entries), len(shipped)


def write(rows, total, shipped):
    by_reason = collections.defaultdict(list)
    for row in rows:
        by_reason[row['reason']].append(row)

    out = [
        '# Ce qui n’est pas retranscrit',
        '',
        f'{shipped} des {total} séquences du répertoire sont jouables dans '
        f'l’application. Voici les {len(rows)} autres, et pourquoi.',
        '',
        '> Généré par `pipeline/held.py`, à partir de la lecture que le '
        'pipeline fait aujourd’hui. Une liste écrite à la main deviendrait '
        'fausse dès que quelque chose se met à marcher.',
        '',
        'La raison donnée est celle qui bloque **le plus grand nombre de '
        'mesures** de la séquence ; le détail par mesure suit chaque entrée. '
        'Une séquence n’est publiée que si au moins une de ses mesures boucle '
        'exactement *et* contient une frappe.',
        '',
    ]
    for key, title, explanation in REASONS:
        group = by_reason.get(key)
        if not group:
            continue
        out += [f'## {title.capitalize()} — {len(group)} séquence'
                f'{"s" if len(group) > 1 else ""}', '', explanation, '']
        for row in sorted(group, key=lambda r: (r['corps'], r['id'])):
            year = f" {row['year']}" if row.get('year') else ''
            drawn = ' · musique tracée en courbes' if row['drawn'] else ''
            detail = ', '.join(f'{n} {k}' for k, n in row['counts'].items())
            out += [
                f"- **{row['corps']}{year} — {row['title']}** "
                f"(`{row['id']}`){drawn}  ",
                f"  {row['bars']} mesure{'s' if row['bars'] > 1 else ''} lue"
                f"{'s' if row['bars'] > 1 else ''}"
                + (f' : {detail}' if detail else '')
                + f"  ",
                f"  [source]({row['url']})",
            ]
        out.append('')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    rows, total, shipped = survey()
    text = write(rows, total, shipped)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'{len(rows)} séquences écartées sur {total} -> {OUT}')
    for key, title, _why in REASONS:
        n = sum(1 for r in rows if r['reason'] == key)
        if n:
            print(f'   {n:>3}  {title}')
