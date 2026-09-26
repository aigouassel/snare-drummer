"""Transcribe named scores, the repertoire, or everything.

Both this and `run/batch.py`'s own entry point go through `batch.run()`: which
scores are worth shipping is one rule, and a rule implemented twice drifts."""
import json
import os

from pipeline import paths, transcribe as transcriber
from pipeline.run import batch

def do_transcribe(args):
    _data, entries = batch.sequences(repertoire=args.repertoire)
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
    batch.run(chosen)
