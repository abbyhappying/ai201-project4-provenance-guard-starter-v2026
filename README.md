# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does



Provenance Guard takes a piece of writing and tells the writer whether it
looks human-written, AI-written, or too close to call — and gives them a way to
appeal if it got them wrong.

### The path a submission takes

| # | Where | What it adds |
|---|---|---|
| 1 | `app.py::submit` receives `POST /submit` | Raw JSON becomes a Python dict. This is the only way in. |
| 2 | Input check, same route | Rejects missing, empty, too-short or too-long `text` (and a missing `creator_id`) with a `400` instead of a crash. Assigns a new `content_id` (UUID). |
| 3 | `detector.py::model_signal` | `model_score`, 0–1: how predictable the text is to GPT-2 (perplexity, squashed onto 0–1). |
| 4 | `stylometry.py::style_signal` | `style_score`, 0–1: the shape of the text — sentence-length spread, vocabulary repetition, punctuation. |
| 5 | `scoring.py::combine_signals` | One `combined_score`, 0–1. This is where the decision about which way to be wrong gets made. |
| 6 | `scoring.py::score_to_label` | A `guess` (`ai` / `human` / `unsure`) and the sentence a person actually reads, chosen by the thresholds in `config.py`. |
| 7 | `audit.py::log_decision`, then the response | A permanent line in `logs/audit.jsonl`, and a JSON response with the label, both signal scores, and the `content_id` the writer needs to appeal. |

All scores point the same way: **higher means more likely AI.**

### Tracing the false positive

**Who:** a student writing in their second language submits an essay they
wrote themselves. Short sentences, common words they're sure of, no semicolons
or dashes.

**What score they get:** GPT-2 finds plain, common wording easy to predict, so
the model signal comes out high — say around 0.85. With the starter settings
(style signal still a stub at 0.5, weights 0.5 / 0.5) the combined score is
0.5 × 0.85 + 0.5 × 0.5 = **0.675**. That is above `AI_THRESHOLD` (0.65), so
they are labelled **high-confidence AI**. *(Illustrative numbers from the
starter configuration — Milestone 4 replaces them with measured ones.)*

**What the label says to them:** in the starter, a placeholder. Even once it's
written, a confident "AI" label reads as an accusation, and the writer has no
way to tell that one signal alone pushed them over the line.

**What they can do about it:** in the starter, nothing — `/appeal` returns
`501`. Once it's built, they can appeal, but only if the response gave them
their `content_id` and the label told them appealing is an option.

**What this means for my design:**

1. The "ai" label has to be hard to reach — a higher AI threshold or a wider
   "unsure" band. That lets more AI text through in exchange for fewer real
   writers being accused, and I'm choosing that trade on purpose.
2. One signal shouldn't be able to convict on its own. A strong model score
   with an ordinary style score should land in "unsure", not "ai".
3. The style signal has to actually work. While it's stuck at 0.5, the model
   signal decides everything — and the model signal is the one with this
   blind spot.
4. Every label, especially "ai", tells the writer they can appeal and gives
   them the `content_id` to do it.

### The endpoint contract

Every error, on both endpoints, has the same shape:
`{"error": "<code>", "message": "<a sentence a person can act on>"}`.

#### `POST /submit`

**Request**

| Field | Type | Rule |
|---|---|---|
| `text` | string | Required. Not empty after trimming. At least a few sentences (under 3 tokens can't be scored). At most 20,000 characters. |
| `creator_id` | string | Required, not empty. Who submitted it; also the rate-limit key in unit 8. |

**Response `200`**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string (UUID) | The handle for `/appeal`. |
| `creator_id` | string | Echoed back. |
| `guess` | `"ai"` \| `"human"` \| `"unsure"` | Machine-readable result. |
| `label` | string | The sentence a person reads, including how to appeal. |
| `confidence` | float, 0–1 | Same value as `combined_score`: **0 = confidently human, 1 = confidently AI.** It is not "how sure we are of the guess". |
| `model_score` | float, 0–1 | Signal one. |
| `style_score` | float, 0–1 | Signal two. |
| `combined_score` | float, 0–1 | The number the label came from. |
| `status` | `"decided"` | Matches the audit log. |

**Errors**

| Status | `error` | When |
|---|---|---|
| `400` | `invalid_input` | `text` missing, not a string, empty, too short or too long; or `creator_id` missing or empty. |
| `429` | `rate_limited` | Too many submissions (unit 8). |
| `503` | `detector_unavailable` | The local model couldn't be loaded. |

#### `POST /appeal`

**Request**

| Field | Type | Rule |
|---|---|---|
| `content_id` | string | Required. Must match an earlier submission in the audit log. |
| `reasoning` | string | Required, not empty. The writer's explanation. |

**Response `200`**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | Echoed back. |
| `status` | `"under_review"` | The item's new status. |
| `message` | string | Confirmation for the writer, e.g. "Your appeal was recorded. A person will review it." |

**Errors**

| Status | `error` | When |
|---|---|---|
| `400` | `invalid_input` | `content_id` or `reasoning` missing or empty. |
| `404` | `not_found` | No submission with that `content_id` — so a typo gets a clear answer instead of a silent success. |

**Not checked (on purpose, for this unit):** whether the person appealing is
the original `creator_id`. The appeal is recorded beside the original decision
— never overwriting it — and a person reviews it.

---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** Perplexity — how easily a local language model (GPT-2,
in `detector.py`) predicts each next word of the text. Low perplexity means
predictable; `model_signal` maps that onto 0–1 so that more predictable scores
higher (more AI-like).

**Why that might differ between human and AI writing:** A language model
writes by repeatedly choosing a likely next word, so its output is text a model
finds easy to predict. People make odder, more specific choices — an unusual
word, an abrupt turn, a detail nobody would guess.

**What it can't see:** Authorship. It rewards *plain* writing, not *machine*
writing. Someone writing in a second language, a younger writer, or anyone
writing simply on purpose uses common words in ordinary sentences — and scores
about as machine-like as a machine. The reverse fails too: AI text dressed up
with rare, ornate vocabulary scores as human, because rare words are exactly
what the model can't predict. The writers this signal is most likely to accuse
are the ones with the least room to argue back.

### Signal two — the style signal

**What it measures:** The shape of the text, without reading it
(`stylometry.py`): how much sentence length varies, how much vocabulary
repeats (type-token ratio), and how much punctuation is used and of what kind
(semicolons and dashes vary more between writers than full stops).

**Why that might differ between human and AI writing:** Generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

**What it can't see:** Meaning. Anything that changes the shape without
changing the substance moves it: splitting or merging sentences, adding typos,
pasting in a quotation, sprinkling in semicolons. Those are cheap to do on
purpose. It is also unreliable on short text — one sentence has no length
spread at all, and type-token ratio falls as text gets longer, so length alone
can look like a signal.

**Why two signals:** they fail on different things. The model signal is
fooled by word choice; the style signal is fooled by structure. An input has to
fool both to get a confident wrong answer.

### The combining rule

<!-- Write the rule in words, then give the numbers. What happens when the two
     signals disagree? -->

**The rule:**

**The numbers:**

**Where it lives:** `scoring.py::combine_signals`

<!-- ⚠️ The grader checks your code against that line. If your rule lives
     somewhere else, say where. -->

**A case where my two signals split, and what my rule does with it:**



---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human |  |  |
| unsure |  |  |
| high-confidence AI |  |  |

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->



---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "...", "creator_id": "..."}'
```

```json

```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "...", "reasoning": "..."}'
```

```json

```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json

```

---

## How I Used AI

**Moment 1**

- *What I asked for:*
- *What came back:*
- *What I changed:*

**Moment 2**

- *What I asked for:*
- *What came back:*
- *What I changed:*

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
