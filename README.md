# srtat

Given a subtitle file and a timestamp, tell me what's being said right then.

I keep running into this from two directions: writing about a scene in a
video and wanting the exact line without scrubbing back and forth, and
checking whether a subtitle track drifted out of sync partway through a
file. Both come down to the same question: "what cue is on screen at time
T?" Most subtitle tools are editors, players, or format converters. None of
them answer that one question directly from the command line.

## Usage

```
$ srtat movie.srt 00:01:23,500
#42
Come with me if you want to live.

$ srtat movie.srt 83.5
#42
Come with me if you want to live.

$ srtat movie.srt 00:00:05,000
(no subtitle at this time)
```

The time argument accepts either an SRT-style timestamp (`HH:MM:SS,mmm`) or
plain seconds, decimals allowed. If two cues overlap at the given moment,
both are printed.

As a library:

```python
from srtat import parse, at

with open("movie.srt", encoding="utf-8-sig") as fh:
    cues = parse(fh.read())

for cue in at(cues, ms=83_500):
    print(cue.text)
```

## What it handles

Real .srt files are messier than the spec suggests. Right now `srtat` copes
with:

- a leading BOM
- CRLF or LF line endings
- a period instead of a comma before milliseconds
- missing or non-numeric index lines
- multi-line cue text
- overlapping cues
- zero-duration cues

Cues with an end time equal to their start time never match a query; a cue
matches from its start time up to (but not including) its end time, so
back-to-back cues don't both claim the boundary millisecond.

## Status

Early. Only the `.srt` format is supported so far. No dependencies beyond
the Python standard library.

## Running the tests

```
python -m unittest discover tests
```
