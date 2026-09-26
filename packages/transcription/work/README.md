# Working directory

Downloaded PDFs, their extracted ink, and the contact sheets used to name
symbols. **Nothing here is committed** — see the allowlist in `/.gitignore`.

That is a decision about what a transcription needs in order to stay
checkable. The scores are other people's transcriptions of copyrighted shows,
hosted elsewhere, and every transcribed piece carries the URL it was read
from: the source is one click from the page that displays it, so a downloaded
copy is a working file and working files are disposable.

To re-derive anything here:

```bash
# fetch a score by its catalogue id
pipeline/.venv/bin/python3 -m pipeline.corpus.fetch <catalogue-id>

# look at the symbols a family uses, to name them
pipeline/.venv/bin/python3 -m pipeline.naming.label 'work/*.pdf' \
    --family Opus --out work/opus-sheet.png --json work/opus-listing.json

# read one score into a piece, and update the manifest with it
pipeline/.venv/bin/python3 -m pipeline.cli transcribe <catalogue-id>
```

The one thing that *is* committed is the vocabulary in
`pipeline/naming/tables/*.json`: the labels read off a contact sheet once per
engraving family. That is the human judgement in this pipeline, it is small,
and it is what makes every other score in the family readable without
re-deriving anything.
