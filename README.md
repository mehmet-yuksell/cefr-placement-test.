# English Placement Test (MVP)

A web-based English placement test that gives a **CEFR-aligned estimate** (A1–C2) in about 15 minutes. It measures grammar, vocabulary and reading, and ends with a diagnostic result card in Turkish (default) or English.

> This is a CEFR-aligned estimate, not an official certification. All item parameters are provisional expert estimates until they are calibrated with real response data. All 144 items are original.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11 or newer is required. `requirements.txt` pins Streamlit 1.66 or newer, because the app uses `st.iframe`, `width="stretch"` buttons and horizontal containers, which older versions lack. The app runs fully offline once installed. On first use it creates `data/placement.db` (SQLite) and `data/secret.key` (the email-hashing key); both are gitignored.

## Development commands

```bash
pip install -r requirements-dev.txt
python tools/validate_bank.py                      # lint the item bank (exit 1 on any error)
python tools/validate_bank.py --show B1-RDG-002    # print an item in full for review
pytest --cov=placement                             # tests and coverage
ruff check .
python tools/simulate.py --n 2000 --seed 42        # synthetic-examinee simulation (--length 40 for a longer variant)
python tools/run_personas.py --lang en --seed 42   # scripted A2/B2/C1 run-through of the real app
```

## How it works

| Module | Responsibility |
|---|---|
| `config.py` | Every design constant. `TEST_LENGTH = 28`; stage sizes (10/10/8), content quotas and the routing mix are derived from it, so a 40-item test needs no code change. |
| `models.py` | Dataclasses: `Item`, `Passage`, `Response`, `Session`, `Result`, `DomainScore`, `TagScore`. |
| `bank.py` | Loads `data/item_bank/*.json`, validates every rule, and offers queries by level, type, domain or skill. |
| `engine.py` | On-the-fly multistage adaptive test (routing → targeted → refinement) plus a fixed-form fallback. |
| `scoring.py` | 3PL with fixed parameters, EAP on an 81-point grid with an N(0, 1) prior, CEFR mapping, level probabilities, borderline rule, sub-scores and tag residuals. Pure functions only. |
| `exposure.py` | No repeats per user (5 full attempts per email fit in the 144-item bank), oldest-seen-first reuse, randomesque selection (N = 5), exposure summaries. |
| `storage.py` | SQLite sessions, per-answer response log (with response time and change count) and exposure counts. WAL mode, a busy timeout and one lock around every statement make concurrent sessions safe. The email is stored only as an HMAC-SHA256 hash, and the resume token only as a SHA-256 hash. |
| `report.py` / `i18n.py` | Result card in TR or EN: headline level, can-do statements, confidence, sub-skills, strengths and focus areas, action plan, missed-item review, disclaimer. |
| `web.py` | Stylesheet and pure HTML builders for the landing page, the test screen and the result page (unit-tested). |
| `app.py` | Streamlit UI only: wires screens to the modules above. Includes resume-after-reload, an "I'm not sure" option (scored as wrong) and a live timer. |

**Test design.**
- **Routing stage:** 10 items aimed at 1 A1, 2 A2, 3 B1, 3 B2 and 1 C1 anchor.
- **Re-estimation:** theta is re-estimated by EAP after the routing stage. The targeted stage then aims at `theta − 0.31`, where an item with c = 0.25 is most informative. The refinement stage aims halfway between theta and the nearest cut score.
- **Content balance:** every position first picks the slot kind (type/domain) furthest behind its quota. Content balance wins over difficulty. When the preferred choice is impossible, the engine relaxes in a fixed, logged order: band fallback → other kind → oldest-seen repeat.
- **Passages:** a passage's questions are always served consecutively within one stage.
- **Going back:** Back/Next buttons and a numbered navigator let the user revisit and change answers in the current part only (`engine.editable_range`). Item choice inside a part never depends on correctness, so changes cannot alter which items appear. The user confirms before a part (or the test) ends, and the part's answers then lock. Going back is disabled when the optional early stop is on.

**Scoring.**
- **Headline level:** the level with the highest posterior probability. The level probabilities and any borderline note appear beneath it.
- **Borderline:** a result is borderline when theta is within 0.30 × SE of a cut score (`config.BORDERLINE_SE_FACTOR`, chosen by simulation; see DECISIONS.md).
- **Sub-skill bands:** shown only when at least 5 items back them.
- **Strengths and focus areas:** skill tags are ranked by observed minus model-expected correct answers, using tags with at least 2 items.

Judgement calls are recorded in [DECISIONS.md](DECISIONS.md), the item-by-item audit in [docs/ITEM_AUDIT.md](docs/ITEM_AUDIT.md), and planned extensions in [docs/EXTENSIONS.md](docs/EXTENSIONS.md).

## Validation

These outputs come from the 144-item bank on 2026-11-01. The simulation figures describe **the algorithm under idealised assumptions, not real-world validity**.

### Gate 1: item bank validation (`python tools/validate_bank.py`)

```
level      cloze   error_id    reading  lexical_p  total
A1             7          6          5          6     24
A2             7          6          5          6     24
B1             7          5          8          4     24
B2             7          5          8          4     24
C1             7          7          5          5     24
C2             7          6          5          6     24
total  144 items, 14 passages
domains: grammar=56, reading=36, vocabulary=52
key is strictly longest option in 24% of items, shortest in 23%

OK: item bank passed all checks.
```

### Gate 2: tests (`pytest --cov=placement`)

142 tests pass. Coverage:

```
src\placement\bank.py         323      4    99%
src\placement\config.py        56      0   100%
src\placement\engine.py       169      0   100%
src\placement\exposure.py      33      0   100%
src\placement\i18n.py          28      0   100%
src\placement\models.py       111      0   100%
src\placement\report.py       100      0   100%
src\placement\scoring.py      103      0   100%
src\placement\storage.py       78      0   100%
src\placement\web.py          117      0   100%
TOTAL                        1118      4    99%
```

The tests cover:
- EAP monotonicity, cut-score boundaries, and all-correct and all-wrong sessions;
- seed reproducibility, and no repeats across 3 attempts (on a synthetic bank large enough to allow it);
- repeats on the real bank happening only through logged relaxation, oldest attempt first;
- passage grouping, quota satisfaction, band fallback, content relaxation, bank exhaustion and early stop;
- storage privacy (no plaintext email in the database);
- end-to-end app flows through Streamlit's AppTest: a full test, quitting early, retaking, a partial result and language switching.

### Gate 3: simulation (`python tools/simulate.py --n 2000 --seed 42`)

Abridged below; the bracketed notes are added. The full output is in `docs/simulation_28.txt`.

```
# Simulation: n=2000, seed=42, length=28, mode=adaptive, true theta ~ N(0, 1.2), bank=144 items / 14 passages

## ideal (n = 2000)
mean test length         28.0
exact CEFR agreement     62.5%
within one level         99.1%
mean SE                  0.483
RMSE of theta            0.512
mean bias of theta       +0.003
labelled borderline      28.6%
confusion matrix (rows = true level, columns = estimated level):
            A1    A2    B1    B2    C1    C2   exact
  A1        38    50     6     0     0     0   40.4%
  A2         9   187   128     4     0     0   57.0%
  B1         1    46   420   132     1     0   70.0%
  B2         0     0   122   411    62     0   69.1%
  C1         0     0     2   115   150    13   53.6%
  C2         0     0     0     5    54    44   42.7%
relaxation events (tests affected): band_fallback=622

## misspecified (n = 2000)      [true b = stored b + U(-0.5, 0.5), true a ~ U(0.7, 1.4)]
exact CEFR agreement     60.1%
within one level         98.7%
mean SE                  0.483
RMSE of theta            0.541
mean bias of theta       -0.072

## oracle ceiling (n = 2000)    [every item exactly at the examinee's information peak]
exact CEFR agreement     63.9%
within one level         99.4%
mean SE                  0.468

## item exposure (ideal scenario)
max exposure rate        61.6%
median exposure rate     13.6%
items never used         3.5%
most exposed             B1-LEX-001 62%, B1-CLZ-006 62%, B1-LEX-002 61%, B1-CLZ-007 60%, B1-CLZ-002 60%

## retakes: 200 examinees x 3 consecutive attempts
attempt 1: mean repeated items 0.0, examinees with any repeat 0%
attempt 2: mean repeated items 0.0, examinees with any repeat 0%
attempt 3: mean repeated items 0.0, examinees with any repeat 0%

GATE within-one-level >= 95% (ideal): 99.1% -> PASS
exact agreement 62.5% vs oracle ceiling 63.9%
```

A 40-item run on the same 144-item bank (`--length 40`, no code change) gives 66.4% exact and 99.6% within one level, against a 65.7% oracle ceiling (`docs/simulation_40.txt`).

**Reading the numbers:**
- **Length, not routing, limits accuracy.** With a = 1 and c = 0.25, 28 items give an SE of about 0.47 even with perfect targeting (the oracle). Each CEFR band is 1.0 wide, so about 40% of results land in a neighbouring band.
- **The remaining 1.4-point gap to the oracle is bank coverage.** Even with 24 items per level, about 31% of tests log at least one band fallback (no unseen item of the required kind within ±0.75 logits). With the old 72-item bank this was 90%, and the gap was 3.5 points.
- **The extremes are weakest.** A1 and C2 have the lowest exact agreement because the N(0, 1) prior shrinks extreme estimates towards the centre while the simulated population has SD 1.2.

### Gate 4: run-through of the real app (`python tools/run_personas.py --seed 42`)

The script drives `app.py` itself through Streamlit's AppTest: email entry, 28 question screens, the result card and database writes. Personas answer correctly with the 3PL probability for their true ability. The seed was fixed at 42 before running. This run used the 144-item bank and the part-end confirmation. At a part end the tool answers the same question twice: the first «Next» asks for confirmation, and the second confirms with a freshly drawn answer. So its random sequence differs from earlier runs, which gave A2/B2/C1 on the 72-item bank. Two of three headlines are one level low here, consistent with about 60% exact agreement.

```
A2-like: true theta -1.5 -> headline A1 (28 answers)
B2-like: true theta +0.5 -> headline B1 (28 answers)
C1-like: true theta +1.5 -> headline C1 (28 answers)
```

The three full result cards are in [docs/run_through_en.md](docs/run_through_en.md) and [docs/run_through_tr.md](docs/run_through_tr.md).

These persona runs were made on the earlier 72-item bank. The seed-42 run is one sample. Across seeds 1–10 the headlines were:

| Persona | Exact level | One level off |
|---|---|---|
| A2-like | 6/10 | 4/10 (B1 ×3, A1 ×1) |
| B2-like | 6/10 | 4/10 (B1 ×3, C1 ×1) |
| C1-like | 5/10 | 5/10 (all B2) |

All 30 runs were within one level, consistent with the simulation. The real server was also started with `streamlit run app.py --server.headless true`; its health endpoint returned `ok` and the page returned HTTP 200.

## Limitations

- **Provisional parameters.** Every difficulty is an expert estimate (CEFR anchor ± 0.3), and every item uses a = 1.0 and c = 0.25. Nothing has been calibrated against real responses, so the cut scores and level labels are not empirically validated.
- **Simulation-only evidence.** The accuracy figures come from simulated examinees who answer according to the same model used for scoring. This is the best case; real examinees, real item behaviour and testlet effects will lower agreement.
- **Precision.** 28 four-option items cannot reach 70% exact CEFR agreement even in theory (oracle ceiling 63.9%). About 28.6% of results are flagged as borderline (was 49% with a 0.5 × SE zone).
- **Bank size (144 items).** A user who retakes with the same email gets entirely new questions for 5 attempts: verified through the real app, and covered by regression tests. From the 6th attempt on, items are reused (oldest-seen first, logged, with a notice on the card). The most-used item still appears in about 62% of first attempts, because B1-centred routing draws on few items per kind.
- **Vocabulary levels** were judged without access to English Vocabulary Profile data; see [docs/ITEM_AUDIT.md](docs/ITEM_AUDIT.md).
- **Not measured:** listening, speaking and writing. The timer is soft: a live clock is shown, but nothing is cut off, and speed is not scored. You can go back and change answers within the current part (10 / 10 / 8 questions). When a part ends, its answers lock, because the next part is chosen from the re-estimated ability.
- **No proctoring or identity checks.** The email is hashed for pseudonymisation only. Anyone with both the database and `data/secret.key` could test whether a given email was used. The email is not verified. An unfinished test can be resumed only in the browser that started it, which holds a random token in the URL (`?resume=...`). Anyone who gets that URL can also resume it, and someone who types another person's email can still start a new test, which ends that person's unfinished one, although they cannot see its answers.
- **Not an official certificate.** The result is a CEFR-aligned estimate.

## Repository layout

```
app.py                     Streamlit UI
data/item_bank/            a1.json … c2.json, passages.json
src/placement/             config, models, bank, engine, scoring, exposure, storage, report, i18n
tools/                     validate_bank.py, simulate.py, run_personas.py
tests/                     pytest suite (synthetic bank fixture in conftest.py)
docs/                      EXTENSIONS.md, ITEM_AUDIT.md, simulation and run-through outputs
DECISIONS.md               judgement calls with reasons
```
