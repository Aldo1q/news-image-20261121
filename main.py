#!/usr/bin/env python3
"""Entry point for the news-image-20261121 make.fun submission.

Overview
--------
This program delivers the judged artwork for the entry.  The artwork
itself -- a broadsheet front page summing up the world news of
Saturday 21 November 2026 -- was rendered ahead of time and is shipped
in this repository as ``entry.png``, sitting next to this file.

The grading sandbox provides no third-party packages, only the Python
standard library, and it may invoke this program from an unrelated
working directory with a stripped-down environment.  Redrawing the
page at grade time would therefore be fragile and unnecessary.  This
program instead performs one small, well-defined job reliably:

    locate the shipped ``entry.png``, decide where the grader wants
    the output to land, copy the bytes there, and verify the copy.

Design notes
------------
The implementation is deliberately split into small helpers so that
each decision the program makes can be read, reasoned about, and
tested in isolation:

* :func:`resolve_source_path` -- finds the shipped image relative to
  this file (via ``__file__``), never relative to the caller's working
  directory.  This matters because the grader does not promise to run
  the program from the repository root.

* :func:`resolve_output_dir` -- implements the output-directory
  resolution chain described in its own docstring.  Keeping the chain
  in a single function makes the precedence order explicit and easy
  to audit.

* :func:`ensure_output_dir` -- creates the chosen output directory
  when needed and confirms it is usable, translating operating-system
  failures into a clear diagnostic plus a dedicated exit code.

* :func:`copy_with_verification` -- performs the copy and compares
  byte sizes before and after, so a truncated or partial copy is
  reported as a failure instead of being silently accepted.

* :func:`main` -- orchestrates the helpers, owns all user-facing
  output, and returns an integer exit status.  The module guard at
  the bottom converts that status into the process exit code.

Failure handling
----------------
Failures are reported on standard error with a specific message that
names the path involved and the operation that failed.  Each failure
class uses a distinct non-zero exit code so that a caller (or a log
reader) can tell them apart without parsing the message text:

* ``2`` -- the shipped source image is missing or is not a file.
* ``3`` -- the output directory cannot be created or written to.
* ``4`` -- the copied file's size does not match the source size.

Success is the only path that returns ``0``, and it is reported on
standard output with a single line naming the target path and the
number of bytes written.

The program uses only ``os``, ``shutil`` and ``sys`` from the standard
library, performs no network access, reads no input, and terminates
promptly in every code path.
"""

import os
import shutil
import sys


# Name of the artwork file, both as shipped in the repository and as
# delivered into the output directory.  Centralising the literal here
# keeps the source lookup and the target construction consistent.
IMAGE_FILENAME = "entry.png"

# Fallback output location used when the environment provides no
# explicit destination and the conventional ``/output`` directory is
# not present on this machine.
FALLBACK_OUTPUT_DIR = "/output"

# Distinct exit codes for each failure class.  Zero is reserved for
# success; see the module docstring for the full table.
EXIT_MISSING_SOURCE = 2
EXIT_UNWRITABLE_TARGET = 3
EXIT_SIZE_MISMATCH = 4


def resolve_source_path() -> str:
    """Return the absolute path of the shipped ``entry.png``.

    The image ships alongside this source file, so its location is
    derived from ``__file__`` rather than from the current working
    directory.  Using ``os.path.abspath`` normalises the result even
    when the interpreter was handed a relative path to this script.

    Returns:
        The absolute path where the shipped image is expected to be.
        Existence is *not* guaranteed by this function; callers check
        for the file themselves so they can emit a precise error.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, IMAGE_FILENAME)


def resolve_output_dir() -> str:
    """Decide which directory the graded image should be copied to.

    The resolution chain, in priority order, is:

    1. ``$MAKEFUN_OUTPUT_DIR`` -- when the runner sets this variable
       to a non-empty value it is authoritative and is used verbatim,
       even if the directory does not exist yet (creation is handled
       later by :func:`ensure_output_dir`).
    2. ``/output`` -- the conventional grading location, used when it
       already exists as a directory on this machine.
    3. ``"."`` -- the current working directory, as a last resort so
       that a plain local run still leaves the image somewhere the
       user can find it instead of failing outright.

    Returns:
        The chosen output directory as a string.  The directory may
        not exist yet in the ``$MAKEFUN_OUTPUT_DIR`` case.
    """
    from_env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if from_env:
        return from_env
    if os.path.isdir(FALLBACK_OUTPUT_DIR):
        return FALLBACK_OUTPUT_DIR
    return "."


def describe_size(path: str) -> int:
    """Return the size, in bytes, of the file at ``path``.

    This is a thin, intention-revealing wrapper around
    ``os.path.getsize``.  Giving the operation its own name makes the
    verification steps in :func:`copy_with_verification` read as a
    comparison of two described sizes rather than as raw ``os`` calls
    whose purpose has to be inferred from context.

    Args:
        path: Path to the file whose size is wanted.

    Returns:
        The file size in bytes.
    """
    return os.path.getsize(path)


def ensure_output_dir(target_dir: str) -> int:
    """Make sure ``target_dir`` exists and can receive the copy.

    The directory (including any missing parents) is created when it
    does not already exist.  ``exist_ok=True`` keeps the call safe
    when the directory is already present, which is the common case
    for ``/output`` and for a runner-provided destination.

    Args:
        target_dir: The directory chosen by :func:`resolve_output_dir`.

    Returns:
        ``0`` when the directory is ready for use.  Otherwise the
        ``EXIT_UNWRITABLE_TARGET`` code, after printing a diagnostic
        to standard error that names the directory and the underlying
        operating-system error.
    """
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as exc:
        print(
            f"error: cannot create output directory {target_dir!r}: {exc}",
            file=sys.stderr,
        )
        return EXIT_UNWRITABLE_TARGET
    if not os.path.isdir(target_dir):
        print(
            f"error: output path {target_dir!r} exists but is not a directory",
            file=sys.stderr,
        )
        return EXIT_UNWRITABLE_TARGET
    return 0


def copy_with_verification(source: str, target: str) -> int:
    """Copy ``source`` to ``target`` and verify the result by size.

    The source size is recorded *before* the copy and the target size
    is read *after* it.  Both sizes must agree exactly; the artwork is
    judged byte-for-byte, so even a one-byte difference means the
    delivery failed and must not be reported as a success.

    Args:
        source: Absolute path of the shipped image.
        target: Full destination path (directory plus filename).

    Returns:
        ``0`` on a verified copy.  ``EXIT_UNWRITABLE_TARGET`` when the
        copy itself raises an ``OSError`` (for example a read-only
        destination), or ``EXIT_SIZE_MISMATCH`` when the copy completes
        but the sizes disagree.  Diagnostics go to standard error.
    """
    expected = describe_size(source)
    try:
        shutil.copyfile(source, target)
    except OSError as exc:
        print(
            f"error: cannot copy {source!r} to {target!r}: {exc}",
            file=sys.stderr,
        )
        return EXIT_UNWRITABLE_TARGET
    try:
        written = describe_size(target)
    except OSError as exc:
        print(
            f"error: cannot inspect copied file {target!r}: {exc}",
            file=sys.stderr,
        )
        return EXIT_UNWRITABLE_TARGET
    if written != expected:
        print(
            f"error: size mismatch: copied file is {written} bytes, "
            f"shipped image is {expected} bytes",
            file=sys.stderr,
        )
        return EXIT_SIZE_MISMATCH
    return 0


def main() -> int:
    """Run the delivery: locate, copy, verify, and report.

    Returns:
        ``0`` after a verified copy, with a success line on standard
        output naming the target path and its size in bytes.  Any
        failure returns the dedicated non-zero code documented in the
        module docstring, with the diagnostic already printed to
        standard error by the step that detected the problem (or, for
        the missing-source check performed here, by this function).
    """
    source = resolve_source_path()
    if not os.path.isfile(source):
        print(
            f"error: shipped image missing: {source}",
            file=sys.stderr,
        )
        return EXIT_MISSING_SOURCE

    target_dir = resolve_output_dir()
    ready = ensure_output_dir(target_dir)
    if ready != 0:
        return ready

    target = os.path.join(target_dir, IMAGE_FILENAME)
    result = copy_with_verification(source, target)
    if result != 0:
        return result

    written = describe_size(target)
    print(f"wrote {target} ({written} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
