import re
from collections import Counter, defaultdict

DEG_MODS = ["very", "so", "too", "quite", "rather", "extremely", "slightly", "somewhat"]
CLOSED_MODS = ["almost", "completely", "entirely", "perfectly"]

REL_SUFFIX = re.compile(r".*(al|ic|ical|ary|ory|ive|ian|ese)$")

def extract_gradable_adjs(docs, nlp, min_count=50):
    # docs = iterable of raw texts
    adj_count = Counter()
    deg_hits = Counter()
    comp_hits = Counter()
    closed_hits = Counter()

    for doc in docs:
        sp = nlp(doc)
        toks = [t.text.lower() for t in sp]
        lems = [t.lemma_.lower() for t in sp]
        pos  = [t.pos_ for t in sp]

        for i, (w, lem, p) in enumerate(zip(toks, lems, pos)):
            if p != "ADJ" or not lem.isalpha():
                continue
            adj_count[lem] += 1

            if i > 0 and toks[i-1] in DEG_MODS:
                deg_hits[lem] += 1
            if i > 0 and toks[i-1] in CLOSED_MODS:
                closed_hits[lem] += 1
            if i > 0 and toks[i-1] in ("more", "less"):
                comp_hits[lem] += 1

    # filter + score
    out = []
    for a, c in adj_count.items():
        if c < min_count:   # tune
            continue
        if REL_SUFFIX.match(a):
            continue

        deg_rate = deg_hits[a] / c
        comp_rate = comp_hits[a] / c
        score = (deg_rate > 0) + (comp_rate > 0) + (deg_rate + comp_rate)

        if deg_rate < 0.001 and comp_rate < 0.0005:
            continue

        scale = "closed" if closed_hits[a] / c > deg_hits[a] / c else "open"
        out.append((a, c, deg_rate, comp_rate, scale, score))

    out.sort(key=lambda r: (r[1], r[5]), reverse=True)  # frequency then score
    return out