"""The front door to the pipeline: list what there is, transcribe some of it.

`run/batch.py` is the measuring instrument -- it reads many scores at once so
that a change to the pipeline can be judged on totals rather than on one happy
example. That is not the shape you want when you have just fixed one thing and
want to see one score, and re-reading a hundred and twenty-eight of them to find
out costs minutes.

So the work is split by intent, not by mechanism. Both go through `batch.run()`:
a rule implemented twice drifts, and here the rule is which scores are worth
shipping.

    python3 -m pipeline.cli list                    # everything, and what came of it
    python3 -m pipeline.cli list --family Ash       # one engraving family
    python3 -m pipeline.cli list --held             # what is not shipped
    python3 -m pipeline.cli show 2019-intro         # one score, in detail
    python3 -m pipeline.cli transcribe 2019-intro   # one score, manifest updated
    python3 -m pipeline.cli transcribe --repertoire # the repertoire, remeasured
"""
import argparse
import sys

from pipeline.cli.listing import do_list, do_show
from pipeline.cli.transcribing import do_transcribe


def main():
    parser = argparse.ArgumentParser(
        prog='pipeline.cli',
        description='lister et retranscrire les partitions du catalogue')
    subs = parser.add_subparsers(dest='command', required=True)

    p = subs.add_parser('list', help="ce qu'il y a, et ce qui en est sorti")
    p.add_argument('--family', help='une famille de gravure (Ash, Maestro, …)')
    p.add_argument('--held', action='store_true',
                   help='seulement les non livrées')
    p.add_argument('--shipped', action='store_true',
                   help='seulement les livrées')
    p.add_argument('--repertoire', action='store_true',
                   help='la saison la plus récente de chaque corps')
    p.add_argument('--probe', action='store_true',
                   help='lire les PDF des non livrées pour nommer leur gravure')
    p.set_defaults(func=do_list)

    p = subs.add_parser('show', help='une partition, en détail')
    p.add_argument('id')
    p.set_defaults(func=do_show)

    p = subs.add_parser('transcribe',
                        help='retranscrire, et mettre le manifeste à jour')
    p.add_argument('ids', nargs='*')
    p.add_argument('--all', action='store_true')
    p.add_argument('--repertoire', action='store_true',
                   help='la saison la plus récente de chaque corps')
    p.set_defaults(func=do_transcribe)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    sys.exit(main())
