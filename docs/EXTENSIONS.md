# Extension points

None of these is built in the MVP. This page describes where each would plug in without restructuring the code.

## (a) Listening items

- **Schema:** add an optional `audio_path` field (relative to `data/audio/`) to `ITEM_FIELDS`/`OPTIONAL_ITEM_FIELDS` in `bank.py`, a new `type` (`listening`, code `LST`) in `TYPE_CODES`, and a `listening` domain in `TYPE_DOMAINS` and `config.SKILL_TAGS` (e.g. "Gist", "Detail", "Speaker attitude").
- **Validation:** check that the audio file exists and that its duration is within limits. Audio clips that carry several questions reuse the passage mechanism (a passage record with `audio_path` instead of `text`).
- **Content balance:** add a `("listening", "listening")` entry to `config.SLOT_SHARES`. Quotas, the engine and the simulation pick it up automatically. Add a `domain_listening` string to `i18n.py` and `"listening"` to `scoring.DOMAINS`.
- **UI:** in `app.py`, render `st.audio(...)` above the question when `audio_path` is set. Decide whether replays are allowed and log replays in the response table.

## (b) Lexical decision and C-test items

- **Lexical decision** (real word vs. pseudo-word) is a two-option item. Add type `lexical_decision` (`LXD`) with exactly two options and a per-type `guessing_c` default of 0.5. `_validate_item` currently requires four options, so make the option count a per-type rule. Many items fit in a minute, which is the most realistic way to raise precision within a 15-minute budget (see the simulation's oracle ceiling).
- **C-test** (a text with the second half of every second word deleted) is a testlet: several gaps scored together. Model it like a passage with one "item" per gap, and consider a polytomous (partial-credit) model in `scoring.py` instead of treating gaps as independent 3PL items.

## (c) Writing scoring

- Writing does not fit the multiple-choice pipeline. Add a separate `writing` task type whose response is free text stored in a new `responses_text` table. Score it either with a human rating interface (an admin screen, out of MVP scope) or with an offline, locally run rubric model.
- Report the writing band as its own sub-score next to the domain bands. Do not merge it into theta unless the two scales are linked through a joint calibration.
- Runtime calls to external LLMs or paid APIs stay excluded unless that constraint is changed explicitly.

## (d) Calibration from the response log

Everything needed is already stored: `responses` keeps the item id, item version, correctness, stage and response time for every answer, including those from abandoned sessions.

1. Export responses for items with `status = provisional`. Keep only completed sessions, or model missingness explicitly.
2. Fit a Rasch or 2PL model, using marginal maximum likelihood or a Bayesian fit with priors centred on the expert `difficulty_b`. Adaptive data is fine for MML because the selection depends only on observed responses.
3. Check item fit (infit/outfit or residual statistics), DIF where groups are available, and local dependence within passages (testlet effects).
4. Write the new `difficulty_b` / `discrimination_a` back to the JSON bank, set `status` to `calibrated`, increment `version`, and document the run (sample size, date, model) in `author_notes`. Retire misfitting items with `status = retired`. The engine already skips retired items.
5. Re-run `tools/simulate.py` with the calibrated parameters, and revisit the cut scores with a standard-setting study before claiming anything beyond "CEFR-aligned estimate".
