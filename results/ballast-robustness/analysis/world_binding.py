#!/usr/bin/env python3
"""§12.4 CEILING PROBE (experiment/world-binding-12.4): how much would the
proposed convert-layer fix buy, measured OFFLINE without touching the pipeline?

§12.4 (results.md) argues the dominant ballast failure is a CONVERT-LAYER bug:
lc_packages binds a stateless/tenseless question to the LATEST world, and
ballast EVENT sentences keep advancing the world chain, so the question ends
up pinned to a world where the answer no longer holds (`pipeline-world-shift`,
the largest no_proof slice, §17.2-§17.3). The proposed fix is to bind the
question to a world VARIABLE instead of a constant.

Rather than edit the convert layer (semantic change in Tanel's code, regression
risk, his design call), this estimates the fix's CEILING from stored traces:
for every case whose question world is PINNED to a constant, re-run the
post-LLM pipeline (logconvert -> semnormalize -> gk, zero LLM calls) twice --
once unchanged ("plain") and once with the question world freed to a fresh
variable ("freed", spot_verify.free_question_world) -- and grade both with the
pipeline's own matcher. The net over the cohort is the most the §12.4 fix could
buy; regressions on currently-correct cases are the spurious-proof cost of
freeing too eagerly (the same risk §16.3 saw with world-merge).

This is read-only and $0; it does NOT implement the fix. If the ceiling is
worthwhile, the actual convert-layer prototype is the next step (same branch).

Result (see EXPERIMENT-world-binding-12.4.md): over 310 pinned candidates the
freed run is +53 vs stored / +47 vs plain, dose-growing (b8 +9, b16 +20,
b32 +24), with only 7 regressions (six at b8, zero at b16/b32). Gate met.

Run:  python3 world_binding.py [-doses 8,16,32]
        [-models gpt,claude,gemini,deepseek] [-b0only] [-limit N] [-verbose]
"""
import os
import sys
import argparse
import common as C
import cause_map as CM

sys.path.insert(0, os.path.join(C.REPO, "llmpipe"))
sys.path.insert(0, os.path.join(C.REPO, "llmpipe", "solver"))

from spot_verify import replay
import globals as G  # noqa: E402


def _matcher():
    import test as _t
    return _t._result_matches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-doses", default="8,16,32")
    ap.add_argument("-models", default="gpt,claude,gemini,deepseek")
    ap.add_argument("-b0only", action="store_true", default=True,
                    help="restrict to cases correct at b0 (default)")
    ap.add_argument("-allcases", dest="b0only", action="store_false",
                    help="score every evaluated case, not just b0-correct")
    ap.add_argument("-limit", type=int, default=0)
    ap.add_argument("-budget", type=int, default=20,
                    help="fixed gk budget (s) for BOTH plain and freed replays; "
                         "world-shift rescues flip fast, so this only caps the "
                         "b32 no-proof churn (default 20)")
    ap.add_argument("-verbose", action="store_true")
    args = ap.parse_args()
    doses = [int(s) for s in args.doses.split(",") if s.strip()]
    models = [x for x in args.models.split(",") if x]
    match = _matcher()
    G.options["prover_seconds"] = args.budget
    G.options["prover_seconds_cli"] = True

    def correct(expected, answer, text):
        if answer is None:
            return False
        s = str(answer)
        if s.startswith("Error") or s.startswith("replay-error"):
            return False
        try:
            return bool(match(expected, s, text, single_stage=False))
        except Exception:
            return False

    scope = "b0-correct only" if args.b0only else "all evaluated"
    print(f"\n==== §12.4 ceiling probe: free the pinned question world "
          f"(offline, $0) ====")
    print(f"scope: {scope}; accuracy of graded cases; plain/freed are gk-replayed "
          f"(fixes=[], gk budget {args.budget}s)\n")
    hdr = (f"{'cell':14s} {'n':>4s} {'cand':>4s} {'stored':>6s} {'plain':>5s} "
           f"{'freed':>5s} {'rescue':>6s} {'regr':>4s} {'drift':>5s}")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    for d in doses:
        for m in models:
            cc = C.load(d, m)
            b0 = C.load(0, m)
            if not cc or not b0:
                continue
            man, rev = C.resolve_manifest(d, cc)
            excl = C.exclusions(d) if rev is not None else set()
            ids = sorted(cid for cid in cc
                         if cid in man and cid in b0 and cid not in excl
                         and (not args.b0only or C.is_correct(b0[cid])))
            acc = {"stored": 0, "plain": 0, "freed": 0}
            cand = 0
            flips = {"rescue": [], "regress": [], "drift": [], "err": []}
            done = 0
            for cid in ids:
                c = cc[cid]
                exp = c.get("expected_answer")
                text = c.get("input_text")
                scor = C.is_correct(c)
                acc["stored"] += scor
                qw = CM.question_world(c)
                pinned = qw not in ("var", "none")
                if not pinned:
                    acc["plain"] += scor
                    acc["freed"] += scor
                    continue
                cand += 1
                if args.limit and done >= args.limit:
                    # un-replayed candidate keeps its stored grade
                    acc["plain"] += scor
                    acc["freed"] += scor
                    continue
                done += 1
                try:
                    p_ans, _np, _ = replay(c)
                    f_ans, _nf, subs = replay(c, freeworld=True)
                except Exception as e:
                    acc["plain"] += scor
                    acc["freed"] += scor
                    flips["err"].append((cid, f"exc:{e}"))
                    continue
                pcor = correct(exp, p_ans, text)
                fcor = correct(exp, f_ans, text)
                acc["plain"] += pcor
                acc["freed"] += fcor
                if str(p_ans).startswith("Error"):
                    flips["err"].append((cid, str(p_ans)[:40]))
                if pcor != scor:
                    flips["drift"].append((cid, str(p_ans)[:25]))
                if fcor and not pcor:
                    flips["rescue"].append(cid)
                if pcor and not fcor:
                    flips["regress"].append(cid)
            rows.append((m, d, rev, len(ids), cand, acc, flips))
            print(f"{m+' b'+str(d):14s} {len(ids):>4d} {cand:>4d} {acc['stored']:>6d} "
                  f"{acc['plain']:>5d} {acc['freed']:>5d} "
                  f"{len(flips['rescue']):>6d} {len(flips['regress']):>4d} "
                  f"{len(flips['drift']):>5d}", flush=True)
            if args.verbose and (flips["rescue"] or flips["regress"] or flips["err"]):
                if flips["rescue"]:
                    print(f"      rescued (plain-wrong -> freed-right): {flips['rescue']}")
                if flips["regress"]:
                    print(f"      REGRESSED (plain-right -> freed-wrong): {flips['regress']}")
                if flips["err"]:
                    print(f"      replay errors: {flips['err']}", flush=True)

    tot = {"stored": 0, "plain": 0, "freed": 0}
    tcand = trescue = tregr = 0
    for m, d, rev, n, cand, acc, fl in rows:
        for k in tot:
            tot[k] += acc[k]
        tcand += cand
        trescue += len(fl["rescue"])
        tregr += len(fl["regress"])
    print("-" * len(hdr))
    print(f"{'TOTAL':14s} {'':>4s} {tcand:>4d} {tot['stored']:>6d} "
          f"{tot['plain']:>5d} {tot['freed']:>5d} {trescue:>6d} {tregr:>4d}")
    print(f"\npure §12.4 effect (freed - plain, replay-controlled): "
          f"{tot['freed'] - tot['plain']:+d}")
    print(f"headline-referenced (freed - stored, incl. convert drift): "
          f"{tot['freed'] - tot['stored']:+d}  "
          f"(plain - stored drift: {tot['plain'] - tot['stored']:+d})")
    print(f"rescues {trescue}  vs  regressions {tregr}  over {tcand} pinned "
          f"candidates  -> net {trescue - tregr:+d}")
    print("Read: a worthwhile ceiling needs rescues >> regressions and a clearly "
          "positive\nfreed-plain. Regressions are the spurious-proof cost of "
          "freeing the question world\n(it can now unify with the wrong world). "
          "freed-plain isolates the fix from convert drift.")


if __name__ == "__main__":
    main()
