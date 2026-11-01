# Decisions

Judgement calls made without asking, each with a one-line reason. Newest last.

## Phase 0 (approved by the product owner)

- **Gate A:** keep 28 items; the gate is within-one-level ≥ 95%, and exact agreement is reported next to an oracle ceiling for the same length. Reason: 70% exact needs about 50 items with a = 1, c = 0.25.
- **Early stop** is "one level has posterior probability ≥ 0.90 after ≥ 20 items", default off. Reason: SE < 0.30 is unreachable in 28 items.
- **No-repeat guarantee** is tested on a synthetic bank big enough to allow it; on the real bank, repeats happen only through logged relaxation. Reason: 72 items cannot give a mid-level user 3 disjoint 28-item tests.
- **On-the-fly MST:** stages are assembled at test time; theta is re-estimated only at stage boundaries. Reason: pre-assembled modules plus no-repeat plus a small bank are incompatible.
- **Integer slot quotas** come from a single `TEST_LENGTH` (default 28) by largest-remainder apportionment; content balance wins over difficulty. Reason: the product owner asked for one length constant.
- **Domain sub-scores** use a per-domain EAP band; % correct is secondary. Reason: in an adaptive test % correct is not comparable between people.
- **Strengths/focus tags** are ranked by observed minus model-expected correct. Reason: raw % correct is confounded by adaptive difficulty.
- **Email identity** is HMAC-SHA256 with an install-local key. Reason: a random per-record salt would make returning users unfindable.
- **Result card headline** is the single most likely level; level probabilities and any borderline note sit beneath it. Reason: product owner's instruction.

## Phase 1

- The project has its own git repo, outside the Obsidian vault. It started in `Desktop\placement_test` and moved to `Desktop\english` at the product owner's request. Reason: keeps code out of personal notes.
- `requirements.txt` installs the package itself (`-e .`) next to Streamlit. Reason: `pip install -r requirements.txt` then `streamlit run app.py` works with no path hacks.
- Added an optional `instruction` field (per-type default when omitted). Reason: the negative-stem rule needs to see the instruction separately from sentence text that may legitimately contain "not".
- Error-identification items come in two styles: `[bracketed]` segments in the stem, or four whole-sentence rewrites. Reason: the brief allows both; brackets make "key = exact option text" safe.
- `skill_tested` is one tag from a controlled list of 20 (10 grammar, 6 vocabulary, 4 reading) in `config.SKILL_TAGS`. Reason: tags must recur to support strengths/focus areas; free text would not.
- Domain is fixed by type, except cloze (grammar or vocabulary). Reason: makes the 40/35/25 domain mix reachable through slot quotas.
- The validator rejects British/American-marked spellings (colour/color, centre/center, ...). Reason: rule 7 (neutral variety) is cheap to enforce for spelling.
- "Explains every distractor" is checked mechanically only for distractors of ≤ 4 words (they must be quoted). Reason: long rewrite options are paraphrased, not quoted.
- Option-length balance: per item, the key may not exceed the longest distractor (or undercut the shortest) by more than max(3 chars, 25%); bank-wide, the key may be strictly longest or shortest in at most 40% of items. Reason: catches the "longest answer" cue without forbidding natural variation.
- C2-ERR-001: the error segment was widened from "are" to "are expected". Reason: the validator flagged the key as conspicuously short, which is a test-wise cue.
- Audit rewrites: A2-RDG-002 "suggest" → "want"; B1-RDG-001 "unsure" → "worried". Reason: both words are above the item's level.

## Phase 2

- Information-peak offset: targets use b = theta - 0.31 (the 3PL information peak for c = 0.25). Reason: aiming b at theta itself wastes information.
- Stage 3 aims halfway between theta2 and the nearest cut score, not at the cut itself. Reason: the brief says "biased toward" the boundary, and halfway keeps items informative for the examinee's own ability as well.
- Relaxation order: in-band unseen → any-distance unseen (`band_fallback`) → other kinds beyond quota (`content_relaxed`) → seen units from the oldest attempt (`repeat`) → end the test (`bank_exhausted`). Reason: the no-repeat promise to users outranks content balance, which outranks difficulty fit.
- A reading passage must fit inside the current stage, and must leave a remaining reading quota of 0 or at least 2. Reason: siblings are served consecutively, and quotas must stay reachable with 2–3-question passages.
- Each random draw uses `Random(f"{seed}:{position}")`. Reason: reproducible from the seed alone, with no RNG state to persist.
- The fixed form ignores the seed and uses N = 1 (closest item). Reason: it exists for debugging and comparison, so every first-time taker should get the same form.
- Level probabilities: a grid point lying exactly on a cut gives half its mass to each side. Reason: otherwise the grid biases probabilities upwards.
- The headline (and the simulation's classification) is the most likely level, not the band of the EAP point. Reason: consistency with the result-card headline.
- Ties in most-likely level go to the lower level. Reason: a conservative placement.
- No result below 10 answers (`MIN_ITEMS_FOR_RESULT`). An abandoned session with at least 10 answers gets a partial result marked incomplete. Reason: EAP with very few answers mostly reflects the prior.
- Retake study: the simulation runs 200 examinees × 3 attempts and reports repeats. The oracle ceiling is simulated with items at each examinee's own information peak. Reason: puts exact agreement next to the best achievable at this length (gate A).
- Misspecification scenario: true b = stored b + U(-0.5, 0.5), true a ~ U(0.7, 1.4). Reason: shows robustness to provisional parameters being wrong.

## Phase 3

- The app keeps the engine state in `st.session_state` and writes every answer to SQLite immediately. Resuming an interrupted session is not supported; starting again marks the old session `abandoned`. Reason: simple and loss-free for the calibration log; resume was not required.
- The soft timer is the elapsed time shown on each question (it refreshes per question, not every second). Reason: a live clock needs custom JavaScript, and timing is display-only.
- Options are shuffled with `Random(f"{seed}:{item_id}")`. Reason: stable across reruns within a session; the key position is never stored.
- `[segment]` markers are rendered underlined and bold, and gaps as escaped underscores. Reason: Markdown would otherwise turn `___` into formatting.
- The result card is rebuilt in the current language on every render. Reason: the TR/EN switch works on the result screen too.
- `PLACEMENT_DB`, `PLACEMENT_KEY` and `PLACEMENT_SEED` environment overrides were added. Reason: tests and the scripted run-through need an isolated database and a reproducible seed; normal use needs none of them.

## Phase 4

- Bank expanded to exactly 72 items (12 per level), with 18 reading items in 8 passages; two new 3-question passages sit at B1 and B2. Reason: 3-question passages make the 7-item reading quota reachable (2 + 2 + 3), and B1/B2 hold most examinees. Quality over count, as instructed.
- Audit of the new items rewrote A2-CLZ-003 ('can' was arguably defensible) and B1-RDG-003 (key said 'members'). Reason: one defensible key.
- The action plan has 4–5 steps: practice for up to 3 focus tags (topped up with the next-weakest tags), a level-appropriate reading habit, and the time estimate. Reason: always tied to the user's own weakest data.
- Time estimate wording: "a widely used rough guide is about 200 hours of guided study per level", with no source link. Reason: commonly cited planning figure; the brief forbids fabricated links.
- Can-do statements are original paraphrases, 2–3 per level, in both languages. Reason: no quoting of Council of Europe text.
- Persona run-through: personas answer probabilistically at theta -1.5 / 0.5 / 1.5 through the real app (AppTest), with seed 42 fixed before running; variability across seeds 1–10 is reported too. Reason: a single scripted run is a sample, not evidence.

## UI redesign (after product-owner feedback "looks terrible"; reference: fielse.com/tr/level-test)

- Ideas borrowed from the reference page (no content, branding or code copied): a landing page with hero, CTA and facts; one question per screen; an "I'm not sure" option; restoring an unfinished test; a CEFR explainer; an FAQ; copying the result; a retake button.
- Stayed on Streamlit (brief constraint) and restyled it with CSS plus HTML fragments from a new pure module, `placement/web.py`. Reason: no frontend build step, and the HTML builders stay unit-testable.
- Answer options are lettered cards (A–D) built by styling `st.radio` with CSS against its react-aria DOM. Reason: one click selects, the existing tests keep working, and there are no rerun-flicker hacks.
- "I'm not sure" (`models.UNSURE`) is a fifth choice and is scored as incorrect. The FAQ says plainly that a guess can be lucky and this option keeps luck out. Reason: the reference offers it; it is not presented as score-maximising, which would be untrue under 3PL.
- No "Back" button. Reason: the test is adaptive, so earlier answers drive item selection (the FAQ explains this). The reference's Back/Next pattern would break routing.
- Resume: on start, an unfinished session for the same email offers "continue" or "start new". Continue rebuilds the engine by replaying the stored answers (`engine.replay`, deterministic from the seed). If the bank changed, the old session is abandoned with a notice. Reason: a browser refresh would otherwise lose the test.
- A live timer is a tiny JavaScript component (display only). This replaces the per-question elapsed caption.
- Result page: a level ring, the CEFR scale with a ±1 SE band, probability bars per level, sub-skill tiles, strength/focus chips, numbered plan steps, a copyable result line and a Markdown download. Reason: makes uncertainty visible instead of one label, which is the main improvement over the reference.
- Theme in `.streamlit/config.toml` (indigo primary, light base). The font stack uses system fonts only. Reason: the app must work offline, so no Google Fonts.
- Inline SVG icons were replaced by text glyphs. Reason: `st.html` sanitises SVG away.
- The FAQ quotes simulation figures (about 99% within one level, about 60% exact) rather than a vague "reliable". Reason: honesty requirement.

## Retakes and bank growth (product owner: "the same user must not see the same questions again")

- Measured through the real app: with 72 items, attempt 2 had 0 repeats, attempt 3 had 12 of 28, and attempt 4 had 28 of 28. The selection logic was already correct (seen items are excluded first); the bank was too small. Reason: no algorithm can avoid repeats when 3 x 28 > 72.
- The bank was doubled to 144 items (24 per level, 14 passages). Per-kind totals are sized for 5 full attempts against per-attempt quotas of 4/4/7/7/6. Reason: 5 attempts x 28 = 140, which is at most 144.
- Verified through the real app ("Ali", an A2-like user, same email, 5 attempts): 0 repeats on every attempt, 140 distinct items. Regression tests: `test_real_bank_gives_five_attempts_without_repeats` (engine, A2/B2/C1 users) and `test_same_email_second_full_attempt_gets_new_questions` (end-to-end through the app).
- Simulation on the 144-item bank (n = 2000, seed 42): exact 62.5% (was 60.4%), within one level 99.1%. Maximum item exposure fell from 100% to 61.6%, and no examinee saw a repeat in the 3-attempt study.
- From the 6th attempt on, repeats are possible again. They are logged, the oldest-seen items are reused first, and the card shows a notice. Reason: unavoidable with a finite bank.
- Identity is the normalised email: "Ali@Example.com " and "ali@example.com" are the same user, but a different email counts as a new user. Reason: no accounts, by design (brief section 2).
- The timer uses `st.iframe` instead of the deprecated `st.components.v1.html`. Reason: deprecation warning in Streamlit 1.66.
