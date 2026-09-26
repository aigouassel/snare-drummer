"""Transcribe named scores, the repertoire, or everything.

Both this and `run/batch.py`'s own entry point go through `batch.run()`: which
scores are worth shipping is one rule, and a rule implemented twice drifts.

`batch` is imported inside the command rather than beside this docstring. It
pulls in the whole reading half of the package, and the CLI loads every
subcommand's module to build its parser -- so a module-level import here is
paid by `list`, which needs nothing but a JSON file. It was: listing what the
catalogue holds failed outright without pymupdf installed."""
from pipeline.corpus import catalogue


def do_transcribe(args):
    _data, entries = catalogue.sequences(repertoire=args.repertoire)
    if args.repertoire or args.all:
        chosen = entries
    elif args.ids:
        by_id = {e['id']: e for e in entries}
        missing = [i for i in args.ids if i not in by_id]
        if missing:
            raise SystemExit(f"inconnu: {', '.join(missing)} — `list` les nomme")
        chosen = [by_id[i] for i in args.ids]
    else:
        raise SystemExit('donner des ids, --repertoire ou --all')

    from pipeline.run import batch

    batch.run(chosen)
