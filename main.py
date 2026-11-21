#!/usr/bin/env python3
"""Entry point for the news-image-20261121 make.fun submission.

The artwork for this entry - a broadsheet front page summing up the
world news of Saturday 21 November 2026 - was rendered ahead of time
and ships in this repository as entry.png, next to this file.

The grading sandbox gives the program no third-party packages, only
the Python standard library, so rather than trying to redraw the page
at grade time this script simply copies the shipped artwork to the
output location. The judged image stays byte-for-byte the one in the
repository, and the program runs cleanly anywhere.
"""

import os
import shutil
import sys


def pick_output_dir() -> str:
    """Decide where the graded image belongs.

    First choice is $MAKEFUN_OUTPUT_DIR when the runner sets it,
    then /output when that directory exists, and finally the current
    working directory so a local run still leaves the file somewhere
    visible.
    """
    from_env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if from_env:
        return from_env
    if os.path.isdir("/output"):
        return "/output"
    return "."


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "entry.png")
    if not os.path.isfile(source):
        print(f"error: shipped image missing: {source}", file=sys.stderr)
        return 1

    target_dir = pick_output_dir()
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, "entry.png")
    shutil.copyfile(source, target)

    # The graded run must hand over exactly the shipped bytes: check
    # the copy landed whole before claiming success.
    shipped = os.path.getsize(source)
    written = os.path.getsize(target)
    if written != shipped:
        print(
            f"error: copy is {written} bytes, shipped image is {shipped}",
            file=sys.stderr,
        )
        return 1
    print(f"wrote {target} ({written} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
