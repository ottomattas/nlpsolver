#!/usr/bin/env python3
"""Token ledger: actual provider-side spend per (dose, model), from the
llm_usage records captured by llmcall.py (plan 02 §1.5).

Records exist only for real API calls -- local LLM-cache hits add none --
so the sums below are the marginal token spend of each run.  USD figures
are list prices (common.PRICES, checked 2026-06-10); provider prompt
caching is already reflected in the per-call raw fields.

Run:  python3 results/ballast-robustness/analysis/token_ledger.py [-live]
      [-doses 2] [-models gpt,claude]
"""
import argparse
import common as C


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("-live", action="store_true")
  ap.add_argument("-doses", default="2")
  ap.add_argument("-models", default="gpt,claude")
  args = ap.parse_args()
  source = "live" if args.live else "snapshot"
  doses = [int(s) for s in args.doses.split(",") if s.strip()]
  models = [m for m in args.models.split(",") if m]

  print("\nToken ledger (real API calls only; list prices)\n")
  hdr = (f"{'model':9} {'dose':>5} {'cases':>6} {'w/usage':>8} {'calls':>6} "
         f"{'in_tok':>12} {'cached_in':>12} {'out_tok':>10} {'USD':>8}")
  print(hdr)
  print("-" * len(hdr))
  grand = 0.0
  for m in models:
    for d in doses:
      cc = C.load(d, m, source)
      t = C.usage_totals(cc)
      grand += t["usd"]
      print(f"{m:9} {'b' + str(d):>5} {len(cc):6d} {t['cases_with_usage']:8d} "
            f"{t['api_calls']:6d} {t['input_tokens']:12,d} "
            f"{t['cached_input_tokens']:12,d} {t['output_tokens']:10,d} "
            f"{t['usd']:8.2f}")
  print("-" * len(hdr))
  print(f"{'TOTAL':9} {'':>5} {'':>6} {'':>8} {'':>6} {'':>12} {'':>12} "
        f"{'':>10} {grand:8.2f}\n")
  print("cached_in: input tokens served from the provider's prompt cache")
  print("(claude: cache reads; its cache WRITES are priced at 1.25x input "
        "and included in USD).\n")


if __name__ == "__main__":
  main()
