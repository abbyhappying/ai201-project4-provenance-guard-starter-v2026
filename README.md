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
| `content_id` | string | Required. Must match an earlier submission in the audit log. Surrounding spaces are ignored, so a pasted reference number still works. |
| `reasoning` | string | Required, not empty. At most 5,000 characters. The writer's explanation. |

**Response `200`**

| Field | Type | Meaning |
|---|---|---|
| `content_id` | string | Echoed back. |
| `status` | `"under_review"` | The item's new status. |
| `message` | string | Confirmation for the writer: "Your appeal was recorded. A person will review it. The original result stays on record until then." |

**Errors**

| Status | `error` | When |
|---|---|---|
| `400` | `invalid_input` | Body isn't a JSON object; `content_id` or `reasoning` missing, empty or not a string; `reasoning` over 5,000 characters. |
| `404` | `not_found` | No submission with that `content_id` — so a typo gets a clear answer instead of a silent success. |

**Not checked (on purpose, for this unit):** whether the person appealing is
the original `creator_id`. The appeal is recorded beside the original decision
— never overwriting it — and a person reviews it. The appeal entry takes its
`creator_id` from the original decision, not from the request.

**Repeat appeals are allowed.** Appealing the same `content_id` again records
another appeal after the first, in order, and returns `200` again — so a
writer can add to their reasoning. The log is append-only, so nothing earlier
is lost.

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

It also can't tell *even* from *machine-made*. Formal human prose with
balanced, equally long sentences reads as AI: the opening of *Federalist
No. 10* has three sentences of almost the same length (spread 0.06), so the
style signal scored it 0.822 — more AI-like than an AI paragraph. Plain
writing with short, steady sentences and few commas has the same problem
(my own paragraph scored 0.552). The writers it misreads are the careful
formal ones and the plain ones — the second group overlaps with signal one's
blind spot, which is why the combining rule won't let "ai" rest on weak
agreement.

**Why two signals:** they fail on different things. The model signal is
fooled by word choice; the style signal is fooled by structure. An input has to
fool both to get a confident wrong answer.

### The combining rule



**The rule:** A weighted average of the two signals, plus an agreement rule:
**a confident label needs both signals on the same side.**

1. Start with the weighted average of the model score and the style score.
2. If *either* signal is below the AI floor, the score is capped just below
   the AI threshold — so it can be "unsure" at worst, never "ai". One signal
   can't convict on its own.
3. If *either* signal is above the human ceiling, the score is raised just
   above the human threshold — so it can be "unsure" at best, never "human".
4. When the signals split, both caps apply and the score is held inside the
   unsure band. **Disagreement always means "unsure".**

The two sides are deliberately unequal. "ai" needs both signals at 0.6 or
more; "human" only needs both at 0.5 or less. A wrong accusation costs the
writer far more than a missed detection costs the site, so the AI side asks
for stronger agreement.

**The numbers:** (all in `config.py`)

| Setting | Value | What it does |
|---|---|---|
| `WEIGHT_MODEL_SIGNAL` | 0.5 | Weight of the model signal in the average |
| `WEIGHT_STYLE_SIGNAL` | 0.5 | Weight of the style signal in the average |
| `AI_FLOOR` | 0.6 | "ai" only if **both** signals are at or above this |
| `UNSURE_CAP` | 0.64 (`AI_THRESHOLD − 0.01`) | Where the score is capped when the AI floor isn't met |
| `HUMAN_CEILING` | 0.5 | "human" only if **both** signals are at or below this |
| `HUMAN_FLOOR` | 0.36 (`HUMAN_THRESHOLD + 0.01`) | Where the score is raised when the human ceiling isn't met |

Equal weights, because each signal was fooled by a different piece in testing
(below) — neither earned more trust than the other. The cap and floor are
worked out from the thresholds, so they stay inside the unsure band if the
thresholds move in Milestone 5.

**Where it lives:** `scoring.py::combine_signals`


**A case where my two signals split, and what my rule does with it:**

Both signals on the same four test pieces:

| Piece | Written by | Model | Style | Average | My rule | Guess |
|---|---|---|---|---|---|---|
| Remote-work paragraph | AI | 0.750 | 0.914 | 0.832 | 0.832 | ai |
| Opening of *Walden* | Human | **0.758** | **0.009** | 0.384 | 0.384 | unsure |
| Casual remote-work paragraph | AI, written casually | **0.445** | **0.752** | 0.599 | 0.599 | unsure |
| Corner-store paragraph | Me | 0.659 | 0.552 | 0.605 | 0.605 | unsure |

**The split: *Walden*.** The model signal scored it as AI (0.758) — perplexity
22, the same as the AI paragraph — most likely because GPT-2 saw this famous
passage in training, so it's predictable whoever wrote it. The style signal
read it as clearly human (0.009): sentences of 51, 8 and 10 words and plenty
of commas. One said AI, the other said human, and the human one was right.
My rule sees the style signal below the AI floor, so "ai" is off the table,
and the model signal above the human ceiling, so "human" is too: the answer is
**unsure**. The writer isn't accused, and the service doesn't claim a
certainty it doesn't have.

**The case that worried me more: the corner-store paragraph.** Here the
signals *agree* — both lean mildly AI on plain, short sentences — and a plain
average of 0.605 is only 0.045 below the AI threshold. A rule that only
handled disagreement wouldn't protect this writer. The AI floor does: the
style score (0.552) is below 0.6, so the score can't reach "ai" however the
thresholds move.

**What it costs:** AI text that gets either signal below 0.6 — by varying
sentence lengths and adding commas, say — can never be labelled "ai", only
"unsure". I'm accepting that trade on purpose (criterion 1).

### The four calibration inputs

Run through the same path as `/submit`: both signals, `combine_signals`, then
`score_to_label`. The AI text is new — not one the style anchors were
calibrated on — so the result isn't rigged by the calibration.

| Input | Model | Style | Combined | Guess |
|---|---|---|---|---|
| Clearly AI (a paragraph on exercise) | 0.925 | 0.836 | 0.880 | **ai** |
| Clearly human (my corner-store paragraph) | 0.659 | 0.552 | 0.606 | **unsure** |
| Formal human (opening of *Federalist No. 10*) | **0.402** | **0.822** | 0.612 | **unsure** |
| Lightly-edited AI (the exercise paragraph, a few words changed, one sentence split, a contraction added) | 0.881 | 0.874 | 0.877 | **ai** |

**Formal human writing — a second split, the opposite way to *Walden*.** The
model signal reads it as human (0.402): Madison's long, Latinate sentences
surprised GPT-2 (perplexity 57.7). The style signal reads it as AI (0.822). That
surprised me, so I printed the three measures: spread was 0.06 — three
sentences of almost identical length — which the spread measure reads as
machine-even rhythm. Punctuation and vocabulary were middling. My rule sees the
model signal below the AI floor and holds the score in **unsure**. The writer
isn't accused.

**Lightly-edited AI — editing barely moved it.** 0.880 before, 0.877 after,
both **ai**. The style score actually went *up* (0.836 → 0.874): splitting a
sentence and dropping commas made the text more even and less punctuated, which
looks more machine-like, not less. Light editing doesn't get AI text past this
detector — which is good for detection, and a warning for criterion 3, which
expects lightly-edited AI to land in "unsure".

**What this tells me:**

- No human text was labelled "ai", and both AI texts were. The AI floor is
  doing its job.
- **No human text reached "human"** — mine 0.606, *Federalist No. 10* 0.612,
  *Walden* 0.384. The model signal scores human writing 0.40–0.76, and the
  style signal's human anchors were set on *Walden*, an extreme case. Ordinary
  human writing doesn't look like that. This puts criterion 3 at risk; the
  fix is recalibrating the style anchors on more of my own writing in
  Milestone 5, not loosening the human ceiling to force a label through.
- Small samples: one run, four texts, and my piece is only 44 words. These
  numbers say where to look, not what's true.


---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | "We think this was probably written by a person." |
| unsure | 0.35 – 0.65 | "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way." |
| high-confidence AI | 0.65 – 1.00 | "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number {content_id}." |

**Why I worded the "unsure" one this way:**

The person reading this may have written every word, so the label must not sound like an accusation. Saying our checks didn't give a clear answer gives them a reason for the non-answer instead of a vague "we're not sure", and it makes clear we are not calling their work AI — we are declining to call it anything.

I first wrote "our two checks disagreed", but that's only true for some "unsure" results. My combining rule puts a text in "unsure" in two situations: when the checks disagree (*Walden*, *Federalist No. 10*), and when they agree but only weakly (my own corner-store paragraph, where both leaned mildly AI). For the second kind, "disagreed" would tell the writer something false. "Didn't give a clear answer" is true in both.


---

## Sample Run



**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

*The full pipeline: both signals, the combining rule, and the real label. The
text is the clearly-AI calibration input: both signals agree (model 0.925,
style 0.836), so the agreement rule lets the weighted average through
unchanged and the guess is `ai`. `confidence` is the combined score — 0 is
confidently human, 1 is confidently AI. The label quotes the `content_id` so
the writer has what they need to appeal.*

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Regular exercise offers numerous benefits for both physical and mental health. It strengthens the heart, improves circulation, and helps maintain a healthy weight. In addition, physical activity releases endorphins, which can reduce stress and improve mood. Experts recommend at least 150 minutes of moderate activity each week. By incorporating exercise into a daily routine, individuals can enhance their overall well-being and quality of life.", "creator_id": "abby"}'
```

```json
HTTP 200
{
  "combined_score": 0.8803,
  "confidence": 0.8803,
  "content_id": "2f5a6cbb-7435-4665-a3f1-2d7cf6d34206",
  "creator_id": "abby",
  "guess": "ai",
  "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 2f5a6cbb-7435-4665-a3f1-2d7cf6d34206.",
  "model_score": 0.925,
  "status": "decided",
  "style_score": 0.8356
}
```

**A bad input** — rejected with a `400`, not a crash, and not logged as a
decision:

```bash
$ curl -X POST http://127.0.0.1:5000/submit \
  -H "Content-Type: application/json" \
  -d '{"text": "Too short to judge.", "creator_id": "abby"}'
```

```json
HTTP 400
{
  "error": "invalid_input",
  "message": "Please submit at least 20 words so there's enough to judge."
}
```

**An appeal**

*Against the submission above, using the reference number from its label.*

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "2f5a6cbb-7435-4665-a3f1-2d7cf6d34206", "reasoning": "Sample appeal for the README: checking that an appeal moves this item to under_review without changing the original decision."}'
```

```json
HTTP 200
{
  "content_id": "2f5a6cbb-7435-4665-a3f1-2d7cf6d34206",
  "message": "Your appeal was recorded. A person will review it. The original result stays on record until then.",
  "status": "under_review"
}
```

An id that was never issued gets a clear answer instead of a silent success:

```bash
$ curl -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{"content_id": "does-not-exist", "reasoning": "test"}'
```

```json
HTTP 404
{
  "error": "not_found",
  "message": "We couldn't find a submission with reference number does-not-exist. Check it matches the one in your result."
}
```

**What the log shows afterwards**

*After the submission and the appeal. Two entries for the same `content_id`:
the original decision, untouched — same guess, same scores, same timestamp —
and the appeal after it, carrying the writer's reasoning and the new status.
Nothing was overwritten; the item's current status is its latest entry. The
decision records both signal scores beside the combined one, so a surprising
result can be traced back to the signal that caused it. The rejected bad input
and the 404 left no entries.*

```bash
$ curl "http://127.0.0.1:5000/log?limit=2"
```

```json
{
  "count": 2,
  "entries": [
    {
      "combined_score": 0.8803,
      "content_id": "2f5a6cbb-7435-4665-a3f1-2d7cf6d34206",
      "creator_id": "abby",
      "guess": "ai",
      "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 2f5a6cbb-7435-4665-a3f1-2d7cf6d34206.",
      "model_score": 0.925,
      "status": "decided",
      "style_score": 0.8356,
      "timestamp": "2026-11-02T07:01:37+00:00"
    },
    {
      "content_id": "2f5a6cbb-7435-4665-a3f1-2d7cf6d34206",
      "creator_id": "abby",
      "event": "appeal",
      "reasoning": "Sample appeal for the README: checking that an appeal moves this item to under_review without changing the original decision.",
      "status": "under_review",
      "timestamp": "2026-11-02T07:16:37+00:00"
    }
  ]
}
```

---

## How I Used AI

**Moment 1**

**Moment 1 — designing the combining rule**

- *What I asked for:* I asked for a way to combine the two signals in
  `scoring.py::combine_signals` that would keep false positives low without
  making the "human" label unreachable, given my criterion that at most 1 in 10
  of my own pieces may be labelled high-confidence AI.

- *What came back:* A weighted average (0.5 / 0.5) plus an "agreement floor":
  a text can be labelled "ai" only if both signals are at or above 0.6,
  otherwise the combined score is capped inside the unsure band. It also
  suggested a symmetric human-side floor so "human" stays reachable.

- *What I changed:* I rejected the first version, which capped the score at
  `AI_THRESHOLD - 0.01` but set the human floor exactly equal to
  `HUMAN_THRESHOLD` — that clause never fired, because `score <= HUMAN_THRESHOLD`
  still matched. I separated the trigger from the pushed value (as the AI side
  already did), moved the human trigger up to 0.5 so both signals only need to
  "lean human", and wrote the rule and its numbers into my README before coding
  it. I also kept equal weights after checking that each signal can be fooled
  on its own.

**Moment 2**

**Moment 2 — debugging the test commands on Windows**

- *What I asked for:* I asked how to send a JSON body to `/submit` and `/appeal`
  from my terminal, and to explain a `Missing file specification after
  redirection operator` error I got.

- *What came back:* An explanation that I was in PowerShell, where `<<'EOF'` is
  bash-only and `curl` is an alias for `Invoke-WebRequest`. It gave two fixes:
  switch to Git Bash, or use PowerShell here-strings plus `curl.exe`.

- *What I changed:* I stayed in PowerShell and used the here-string form with
  `curl.exe`, then verified each response by hand rather than trusting the
  commands blindly — this is how I found that the first human sample scored
  0.6586 and was labelled "ai", which I recorded as a real false-positive case
  for my criteria.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 5 per minute, 50 per day

**Why those numbers and not others:**
A real writer pastes text, reads the result, edits, and resubmits — at least
15–30 seconds per round, so 2–3 a minute at most. Five per minute leaves room
for a double-click or a quick fix-and-resend, but a script sending dozens of
requests per second hits the cap in seconds. The daily limit is what actually
stops a patient script that pauses between requests to stay under the
per-minute cap: mapping my thresholds takes about 1,000 variations, and at 50 a
day from one `creator_id` that is 20 days of probing. I chose 5/50 over the
starter 10/200 because it cuts probing time from about 5 days to 20 and makes
the flood test unambiguous — a limit below 15 is the only way `--flood 15` can
show a 429 at all.

**What a caller counts as:** a `creator_id`. If the request has no usable
`creator_id`, `app.py` falls back to the caller's IP address. This fails in
both directions: one script can send each request under a new `creator_id` and
look like a thousand different callers, and one household or office behind a
single IP can look like one caller. Per-creator limits are cheap to dodge and
easy to share, which is why the audit log is the second half of the defence —
many near-identical submissions from `creator_id`s I have never seen before is
the pattern to look for.

**The run of status codes when I pushed past it:**

200 200 200 200 200 429 429 429 429 429 429 429 429 429 429

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
