# Canonical word forms for semantic normalisation.
#
# Format: {variant: canonical}
# Applied unconditionally (after antonym resolution) to all eligible atom arguments.
# Eligible: bare string, not a URL, not a ?:-variable, not an internal marker.
#
# Keep entries compact: one per line, no extra spaces.

# Prepositions / spatial relations
CANONICALS_PREP={
"inside":"in",
"within":"in",
}

# Nouns (e.g. appear as second arg in ["isa","auto",...])
CANONICALS_NOUN={
"auto":"car",
"automobile":"car",
}

# Verbs / adjectives
CANONICALS_VERB={
"awake":"wake",
}

# Combined map used at runtime — import only this from other modules.
CANONICALS={**CANONICALS_PREP,**CANONICALS_NOUN,**CANONICALS_VERB}
