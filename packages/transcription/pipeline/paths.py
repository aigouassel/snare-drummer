"""Where everything lives, decided once.

Four modules used to work this out for themselves, each counting `..` from its
own file. That is a rule written four times, and moving one module a directory
deeper silently pointed one of them at nothing -- the pipeline's own recurring
failure, applied to itself. Anchored here on the package, depth stops mattering.
"""
import os

PIPELINE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(PIPELINE)                    # packages/transcription
PACKAGES = os.path.dirname(PACKAGE)

CATALOGUE = os.path.join(PACKAGES, 'catalogue', 'src', 'catalogue.json')
WORK = os.path.join(PACKAGE, 'work')
CORPUS = os.path.join(WORK, 'corpus')
PIECES = os.path.join(PACKAGE, 'src', 'pieces')
HELD_BACK = os.path.join(PACKAGE, 'HELD-BACK.md')
TABLES = os.path.join(PIPELINE, 'naming', 'tables')
