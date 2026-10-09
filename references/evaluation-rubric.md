# Evaluation Rubric

The criteria and weights live in `config.json` → `evaluation_criteria` (that's what the
evaluation page reads; change them there). This file defines what each score means so that
Claude's `ai_review` scores and the user's scores use the same scale.

## Scale (every criterion)

| Score | Meaning |
|---|---|
| 1 | Poor: works against the brand or is broken |
| 2 | Weak: noticeable problems, needs rework |
| 3 | Acceptable: does the job, unremarkable |
| 4 | Strong: clearly good, minor tweaks at most |
| 5 | Excellent: would present to a client as is |

Total = Σ (weight × score / 5), out of 100. Unscored criteria count as 0 and the page shows how
many are scored, so a half-scored design never outranks a fully scored one by accident.

## Criteria — what to look at

| Id | Criterion | Weight | Look at | 5 looks like | 1–2 looks like |
|---|---|---|---|---|---|
| `fit` | Business fit | 20 | All three | You'd guess the business type and price level instantly | Could be any industry, or signals the wrong one |
| `distinct` | Distinctiveness | 15 | Logo | Unlike category clichés (`business-types.md`) | Chef hat / gear / globe / swoosh |
| `memorable` | Memorability | 15 | Logo | Describable in one sentence, recallable | Busy, many ideas at once |
| `versatile` | Versatility | 10 | Logo | Reads at 32px, in one colour, reversed | Fine detail, many colours, gradients |
| `craft` | Visual appeal & craft | 15 | All three | Balanced, polished, no defects | Misspelled name, warped letters, artefacts |
| `story` | Story clarity | 10 | Story graphic | Sequence and message clear in 3 seconds | Confusing, generic stock-like scenes |
| `card` | Business card | 10 | Card | Professional, printable, on-brand | Logo wrong/missing, gibberish text, cluttered |
| `coherence` | Coherence | 5 | All three | Unmistakably one brand | Logo or palette changes between assets |

## Rules for Claude's scores

- **Look at the images.** Read every PNG before scoring; never score from the idea text.
- **Generation defects cap `craft` at 2** (misspelled brand name, logo on the card differs from
  the logo, invented text) and must be listed in `flags`. Prefer re-rolling the asset and then
  scoring the fixed version.
- **Use the whole scale.** Five ideas all at 4 tells the user nothing. Rank honestly; it's
  fine for one idea to score in the 50s.
- **Judge `distinct` against the business type's clichés**, not against the other four ideas.
- Claude's scores are a reference and are **not shown on the evaluation page**, which is
  client-facing and never mentions Claude. Give the ranking, comments and flags in chat; the
  user's scores decide. Say so when presenting.

## Reading the results

When the user exports scores (JSON) and shares the file, or reports their picks:
- The winner is the highest total; check `shortlisted` too, since users often shortlist the one they
  love even when another scored higher. Ask if those disagree.
- Look at low criteria on the winner: they're the refinement brief for the next round
  (e.g. winner scored 2 on `versatile` → simplify the symbol in `logo_refine.txt`).
- Big gaps between Claude's and the user's scores on `fit` usually mean the brief missed
  something about the business. Ask about it.
