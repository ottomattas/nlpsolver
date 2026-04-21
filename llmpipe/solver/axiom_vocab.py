# Axiom vocabulary extraction and caching.
#
# Extracts content words from axiom files (axioms_std.js etc.) and caches
# them in a sibling .vocab file. The vocab file is auto-rebuilt when the
# axiom file is newer.
#
# Used by lc_postprocess.py to restrict soft synonym / exclusion axiom
# injection to pairs where both sides appear in the problem or axioms.

import os
import re
import json

import globals as _g


def load_axiom_vocab(axiom_paths=None):
    """Load or rebuild vocab for the given axiom file paths.

    Returns a frozenset of lowercase content words found in the axiom files.
    If axiom_paths is None, uses the default from globals.options.
    """
    if axiom_paths is None:
        opts = _g.options
        if opts.get("prover_axiomfiles"):
            axiom_paths = list(opts["prover_axiomfiles"])
        else:
            axiom_paths = [_g.prover_axiomfile]

    all_words = set()
    for path in axiom_paths:
        all_words |= _load_single_vocab(path)
    return frozenset(all_words)


def _load_single_vocab(axiom_path):
    """Load or rebuild vocab for one axiom file. Returns a set of words."""
    vocab_path = axiom_path + ".vocab"

    # Check if cached vocab is up to date.
    if os.path.exists(vocab_path) and os.path.exists(axiom_path):
        if os.path.getmtime(vocab_path) >= os.path.getmtime(axiom_path):
            return _read_vocab(vocab_path)

    # Rebuild.
    words = _extract_vocab(axiom_path)
    _write_vocab(vocab_path, words)
    return words


def _read_vocab(vocab_path):
    """Read a .vocab file (one word per line)."""
    words = set()
    with open(vocab_path, encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                words.add(w)
    return words


def _write_vocab(vocab_path, words):
    """Write a .vocab file (one word per line, sorted)."""
    try:
        with open(vocab_path, "w", encoding="utf-8") as f:
            for w in sorted(words):
                f.write(w + "\n")
    except OSError:
        pass  # non-fatal — vocab will be rebuilt next time


def _extract_vocab(axiom_path):
    """Extract content words from an axiom .js file."""
    try:
        with open(axiom_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return set()

    # Strip JS comments (// and /* */).
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    # Parse as JSON.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()

    # Walk and collect content words.
    words = set()
    _walk_collect(data, words)
    return words


def _walk_collect(obj, words):
    """Recursively walk a JSON structure and collect eligible content words."""
    if isinstance(obj, list):
        if not obj:
            return
        first = obj[0]
        if isinstance(first, list):
            # List of lists (disjunctive clause or top-level array).
            for item in obj:
                _walk_collect(item, words)
        elif isinstance(first, dict):
            # List of dicts (clause list with @logic/@name).
            for item in obj:
                _walk_collect(item, words)
        elif isinstance(first, str):
            # Atom: position 0 is predicate (skip), positions 1+ are arguments.
            for i in range(1, len(obj)):
                arg = obj[i]
                if isinstance(arg, list):
                    # Skip $ctxt terms.
                    if arg and isinstance(arg[0], str) and arg[0].startswith("$ctxt"):
                        pass
                    else:
                        _walk_collect(arg, words)
                elif isinstance(arg, str) and _eligible(arg):
                    words.add(arg.lower())
    elif isinstance(obj, dict):
        for key in ("@logic", "@question"):
            if key in obj:
                _walk_collect(obj[key], words)


def _eligible(s):
    """True if s is a content word (not a variable, URL, or internal marker)."""
    if not s:
        return False
    if s.startswith("http"):
        return False
    if s.startswith("?:"):
        return False
    if s.startswith("$"):
        return False
    if s.startswith("@"):
        return False
    return True
