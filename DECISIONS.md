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

## Going back within a part (product owner request, supersedes "No Back button")

- Users may go back and change answers only inside the current part. Reason: inside a part, item selection depends on the part's targets, content quotas, exposure and the seed, never on correctness (`_select_unit` reads no answers). So changes there cannot change which items appear, and `engine.replay` still rebuilds the same sequence. Theta is re-estimated at a part boundary and drives the next part, so earlier parts lock.
- One helper, `engine.editable_range(state)`, defines what is editable; the engine, app, navigator and tests all use it. It returns an empty range when the test is finished or when early stop is on, because a changed answer could reverse a stopping decision already taken.
- `engine.change_answer` only flips `state.answers[position]`. It never selects items, crosses a boundary or re-estimates theta.
- `storage.update_response` updates the stored answer in place, adds the revisit time to `response_time_s` and counts `changes`. It does not count exposure again. A safe `ALTER TABLE` migration adds `changes` to older databases.
- Navigating (Back, a navigator box) never saves an unsaved selection; only «Next» saves. Reason: auto-saving on Back from the front question would submit it, which can end a part and lock it without the user confirming. This behaviour is covered by `test_unsaved_selection_is_lost_when_navigating_away`.
- Part-end confirmation is implemented by relabelling the same `next` button («Finish this part» / «Finish the test») and adding a «Review answers» button. Reason: the existing tests and the persona tool click `next` repeatedly, so they keep working unchanged, and the user still has to confirm explicitly.
- «Finish the test» (quit) while a part-end confirmation is pending first saves the confirmed choice. Reason: the user already chose it and pressed «Next»; dropping it would silently lose an answer.
- Navigator box states are current, answered (editable), next, locked and not reached yet. Each state differs in fill and border style and in text (tooltip `help`), and locked boxes also show a lock badge, so colour is never the only cue. A legend explains them. Boxes are 40 px squares in a wrapping horizontal container: 6 per row at 375 px, with no horizontal scroll (verified: `scrollWidth` 375).
- Back/Next stay side by side on phones (CSS on the `navbtns` container), as the request put Back on the left and Next on the right.
- Response time: `shown_at` resets whenever the displayed question changes, so time on an earlier visit to the front question is not added when it is finally answered. Revisit time on an edited answer is added to that answer.
- The persona tool and the 116 earlier tests pass unchanged. The persona tool now draws a second random answer at each part end (it clicks «Next» twice), so its seed-42 headlines changed; the README reports the new values.

## Phase 2 fixes

- `requirements.txt` now pins `streamlit>=1.66`. Reason: the code uses `st.iframe`, `width="stretch"` and `st.container(horizontal=True)`, which `>=1.40` would not guarantee.
- Option-length balance: the key was the strictly longest option in 32% of items (46/144) and the strictly shortest in 6% (8/144). Distractors were lengthened, never the key changed, in 27 items (mostly reading and register items, whose options are phrases), giving 24% longest and 23% shortest; the target was 22–27% for both. Keys, meanings, misconceptions and levels are unchanged. Each edited item's `version` went up by 1, and `docs/ITEM_AUDIT.md` notes the change. Reason: with four options an unbiased bank has the key longest about 25% of the time; 32% is a test-wise cue.
- `validate_bank.py` now prints a warning (not an error) when the key-longest share exceeds 30%; the hard error stays at 40%. Reason: the product owner asked for a warning-level check.
- Version changes do not break resuming. Replay matches items by id, and `item_version` is only recorded for calibration. This is covered by `test_resume_ignores_item_version_changes`, which rewrites stored versions before resuming.
- Simulations regenerated on the 144-item bank: 28 items gives 62.5% exact and 99.1% within one level (unchanged, as expected, because option wording does not enter the model); 40 items gives 66.4% exact and 99.6% within one level, against a 65.7% oracle ceiling.

## Phase 3: measurement quality (simulation first, n = 2000, seed 42, 28 items, 144-item bank)

**Borderline zone.** The factor is now a parameter of `scoring.borderline_with` (default `config.BORDERLINE_SE_FACTOR`). The headline level is the most likely level whatever the factor, so headline accuracy cannot change. The factor only decides how often the card adds "you are near the X/Y boundary". So accuracy was judged on the clear results and on coverage (true level = headline, or = the named neighbour when flagged):

| factor | flagged borderline | exact (headline) | exact among clear results | coverage |
|---|---|---|---|---|
| 0.50 (old) | 48.9% | 62.5% | 69.7% | 82.2% |
| 0.40 | 38.2% | 62.5% | 69.2% | 79.1% |
| 0.35 | 33.7% | 62.5% | 68.1% | 77.3% |
| **0.30 (chosen)** | **28.6%** | **62.5%** | **67.3%** | **75.3%** |
| 0.25 | 23.2% | 62.5% | 66.7% | 73.4% |

- Decision: 0.30. Reason: it is the only tested value inside the requested 25–30% band, and headline accuracy is unchanged. The price is that results shown as clear are exact 67.3% instead of 69.7% (−2.4 points), and coverage falls from 82.2% to 75.3%: fewer warnings means some near-boundary results are no longer flagged. 0.25 overshoots the band and costs more; 0.35 stays above it.

**Routing mix with a C2 anchor (not adopted).**

| routing (10 items) | exact | within one | A1 exact | C2 exact |
|---|---|---|---|---|
| 1 A1, 2 A2, 3 B1, 3 B2, 1 C1 (current) | 62.5% | 99.1% | 40.4% | 42.7% |
| 1 A1, 2 A2, 2 B1, 3 B2, 1 C1, 1 C2 | 62.6% | 99.1% | 42.6% | 38.8% |
| 1 A1, 2 A2, 2 B1, 2 B2, 2 C1, 1 C2 | 62.0% | 99.0% | 41.5% | 38.8% |
| 2 A1, 2 A2, 2 B1, 2 B2, 1 C1, 1 C2 | 61.8% | 99.0% | 40.4% | 40.8% |

- Decision: keep the current routing. Reason: no variant improves C2 (all are lower), the A1 gains are within sampling noise (about 94 true-A1 and 103 true-C2 examinees, so ±5 points), and overall exact agreement does not improve. The extremes are limited by the N(0, 1) prior shrinking extreme estimates and by test length, not by where routing starts. The targeted and refinement stages already move to the extremes after 10 items.

**"I'm not sure".** It is still scored as wrong. A short note now appears under the options on every question ("«Emin değilim» yanlış sayılır; tahmin etmek şans eseri doğru çıkabilir." / "“I'm not sure” counts as wrong; a guess might be right by luck."), and the existing FAQ entry already says the same. Reason: users should know the consequence before choosing it.
