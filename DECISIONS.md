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

- Project lives in `C:\Users\mehme\Desktop\placement_test`, its own git repo, outside the Obsidian vault. Reason: keeps code out of personal notes.
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
