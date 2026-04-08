# Directional antonym pairs for semantic normalisation.
#
# Format: {word: antonym}
# Meaning: flip the polarity of the enclosing atom AND replace word with antonym.
# Applied regardless of current polarity:
#   positive "outside" → negative "inside"  (→ "in" via CANONICALS)
#   negative "outside" → positive "inside"  (→ "in" via CANONICALS)
# Only the non-canonical direction is stored; canonicals.py further reduces the antonym.
#
# Keep entries compact: one per line, no extra spaces.
ANTONYMS={
"outside":"inside",
"below":"above",
"unfinished":"finished",
"incomplete":"complete",
"undone":"done",
}
