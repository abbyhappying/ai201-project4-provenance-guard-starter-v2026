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

Run: `python run_attacks.py --set attack_set`, 2026-11-07 09:36, 56 attacks,
with limits of 5 per minute and 50 per day. The service never crashed and no
request returned a 5xx.

| ID | Family | Status | Guess | Held / Broke |
|---|---|---|---|---|
| EV01 | evasion | 200 | unsure | broke |
| EV02 | evasion | 200 | unsure | broke |
| EV03 | evasion | 200 | ai | held |
| EV04 | evasion | 200 | ai | held |
| EV05 | evasion | 200 | unsure | broke |
| EV06 | evasion | 200 | unsure | broke |
| EV07 | evasion | 200 | unsure | broke |
| EV08 | evasion | 400 | — | held |
| EV09 | evasion | 200 | ai | held |
| EV10 | evasion | 200 | ai | held |
| FP01 | false_positive | 200 | unsure | held |
| FP02 | false_positive | 200 | ai | broke |
| FP03 | false_positive | 200 | ai | broke |
| FP04 | false_positive | 200 | ai | broke |
| FP05 | false_positive | 200 | ai | broke |
| FP06 | false_positive | 200 | unsure | held |
| FP07 | false_positive | 200 | unsure | held |
| FP08 | false_positive | 400 | — | held |
| PI01 | prompt_injection | 200 | unsure | held |
| PI02 | prompt_injection | 200 | unsure | held |
| PI03 | prompt_injection | 200 | unsure | held |
| PI04 | prompt_injection | 200 | unsure | held |
| PI05 | prompt_injection | 200 | unsure | held |
| PI06 | prompt_injection | 200 | unsure | held |
| MF01 | malformed | 400 | — | held |
| MF02 | malformed | 400 | — | held |
| MF03 | malformed | 400 | — | held |
| MF04 | malformed | 400 | — | held |
| MF05 | malformed | 400 | — | held |
| MF06 | malformed | 400 | — | held |
| MF07 | malformed | 400 | — | held |
| MF08 | malformed | 400 | — | held |
| RQ01 | malformed | 400 | — | held |
| RQ02 | malformed | 400 | — | held |
| RQ03 | malformed | 400 | — | held |
| RQ04 | malformed | 400 | — | held |
| RQ05 | malformed | 400 | — | held |
| RQ06 | malformed | 400 | — | held |
| RQ07 | malformed | 400 | — | held |
| RQ08 | malformed | 400 | — | held |
| RQ09 | malformed | 400 | — | held |
| RQ10 | malformed | 429 | — | held |
| RQ11 | malformed | 429 | — | held |
| RQ12 | malformed | 400 | — | held |
| FL01_01 | flood_same_creator | 400 | — | held |
| FL01_02 | flood_same_creator | 400 | — | held |
| FL01_03 | flood_same_creator | 400 | — | held |
| FL01_04 | flood_same_creator | 400 | — | held |
| FL01_05 | flood_same_creator | 400 | — | held |
| FL01_06 | flood_same_creator | 429 | — | held |
| FL01_07 | flood_same_creator | 429 | — | held |
| FL01_08 | flood_same_creator | 429 | — | held |
| FL01_09 | flood_same_creator | 429 | — | held |
| FL01_10 | flood_same_creator | 429 | — | held |
| FL01_11 | flood_same_creator | 429 | — | held |
| FL01_12 | flood_same_creator | 429 | — | held |

| Family | Attacks | Held | Broke |
|---|---|---|---|
| evasion | 10 | 5 | 5 |
| false_positive | 8 | 4 | 4 |
| prompt_injection | 6 | 6 | 0 |
| malformed | 20 | 20 | 0 |
| flood_same_creator | 12 | 12 | 0 |

**47 held, 9 broke.**

How the rows were marked: an evasion broke if the AI text escaped "ai"; a
false positive broke if human text came back "ai"; a prompt injection broke if
it forced a confident verdict; a malformed request broke only on a 5xx; the
flood held because 429s appeared. A few rows need a caveat:

- **EV08 and FP08** returned 400 because they are under the 20-word minimum, so
  they were never scored. FP08 is real human writing that was refused, not one
  that was protected.
- **RQ10 and RQ11** returned 429 before validation ran. Their bodies give the
  limiter no usable `creator_id`, so they were counted against the shared
  per-IP bucket, which RQ02, RQ06, RQ07, RQ08 and RQ09 had already filled.
  How the service handles form-encoded and `text/plain` bodies was never tested.
- **FL01_01–05** returned 400 because the flood text is under 20 words. The
  limiter counted them anyway, and FL01_06–12 returned 429.

**Ten audit log entries from the run**


```json
{"timestamp": "2026-11-07T17:36:07+00:00", "content_id": "fb098404-6c21-4696-a055-658c20ca2b15", "creator_id": "attacker_FP03", "guess": "ai", "model_score": 0.8051, "style_score": 0.7644, "combined_score": 0.7848, "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number fb098404-6c21-4696-a055-658c20ca2b15.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:07+00:00", "content_id": "c6a2a9c1-8d77-4933-8952-db73ff706d89", "creator_id": "attacker_FP04", "guess": "ai", "model_score": 0.8329, "style_score": 0.7281, "combined_score": 0.7805, "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number c6a2a9c1-8d77-4933-8952-db73ff706d89.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:07+00:00", "content_id": "26bd8712-eb64-4a42-8ff1-4b1838cd69e2", "creator_id": "attacker_FP02", "guess": "ai", "model_score": 0.7387, "style_score": 0.7858, "combined_score": 0.7623, "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 26bd8712-eb64-4a42-8ff1-4b1838cd69e2.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:04+00:00", "content_id": "3b30806f-6181-4b1c-8dc7-7acd9d6b0b97", "creator_id": "attacker_EV03", "guess": "ai", "model_score": 0.6662, "style_score": 0.659, "combined_score": 0.6626, "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 3b30806f-6181-4b1c-8dc7-7acd9d6b0b97.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:06+00:00", "content_id": "5add58b9-ed40-49ab-a03a-02e3599d7a26", "creator_id": "attacker_EV10", "guess": "ai", "model_score": 0.9792, "style_score": 0.6061, "combined_score": 0.7926, "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 5add58b9-ed40-49ab-a03a-02e3599d7a26.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:05+00:00", "content_id": "ea6616af-a79f-4702-b5fd-d54e4d30cf23", "creator_id": "attacker_EV05", "guess": "unsure", "model_score": 0.3212, "style_score": 0.3919, "combined_score": 0.3566, "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:04+00:00", "content_id": "11fac502-59fc-4d97-8d4e-a6bc586f1624", "creator_id": "attacker_EV01", "guess": "unsure", "model_score": 0.1635, "style_score": 1.0, "combined_score": 0.5817, "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:08+00:00", "content_id": "a49de798-ce39-40fc-ba55-d39bd3e8bc8f", "creator_id": "attacker_FP06", "guess": "unsure", "model_score": 0.8814, "style_score": 0.4888, "combined_score": 0.64, "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:08+00:00", "content_id": "fcf6389a-e144-4262-9f70-7dd12202cd98", "creator_id": "attacker_FP07", "guess": "unsure", "model_score": 0.8816, "style_score": 0.3, "combined_score": 0.5908, "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:09+00:00", "content_id": "8f86662d-b853-457b-9b3e-b5a26039973c", "creator_id": "attacker_PI05", "guess": "unsure", "model_score": 0.6401, "style_score": 0.45, "combined_score": 0.5451, "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.", "status": "decided"}
{"timestamp": "2026-11-07T17:36:10+00:00", "creator_id": "attacker_flood", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
{"timestamp": "2026-11-07T17:36:10+00:00", "creator_id": "unknown", "event": "rejected", "status": "rejected", "reason": "rate_limited", "limit": "5 per 1 minute"}
```

1. **FP03**: A non-native speaker's careful human writing was labelled "ai" at 0.785, with both signals above 0.76.
2. **FP04**: A human student essay written to a rubric was labelled "ai" at 0.781, so formulaic structure alone gets a real student accused.
3. **FP02**: Formal human writing was labelled "ai" at 0.762, so register alone pushes both signals past the AI floor.
4. **EV03**: This evasion was still labelled "ai", but only 0.013 above the 0.65 threshold, so it nearly escaped.
5. **EV10**: This evasion was still labelled "ai" at 0.793, because repeated structure drove the model signal to 0.979.
6. **EV05**: Heavily edited AI text scored 0.357, only 0.007 above the 0.35 human threshold, so it nearly passed as human.
7. **EV01**: Typos dropped the model signal to 0.164 while the style signal stayed at 1.0, and the full disagreement produced "unsure".
8. **FP06**: Human text with a 0.881 model signal was held at the 0.64 unsure cap, because its style signal was below the AI floor.
9. **FP07**: Human text with deliberate repetition had a 0.882 model signal, and only the 0.30 style signal kept it out of "ai".
10. **PI05**: The audit-log injection failed, because the logged entry has one clean `guess` and `combined_score` and none of the injected values.
11. **Flood rejection**: The 429s from the flood were logged under `attacker_flood`, so the rate limiter leaves a visible trace.
12. **`unknown` rejection**: RQ10 got a 429 under `unknown`, because requests with no usable `creator_id` share one per-IP bucket.

**The single worst outcome**

The row I would least want to explain is FP04: a human-written essay that
came back `guess: "ai"` at `combined_score` 0.7805, with `model_score`
0.8329 and `style_score` 0.7281.

It is the hardest to defend because both signals agreed, and both were well
above the AI floor, so none of my safety rules fired. There is no single
signal to point at and say "this one was wrong" — the service was confident
from two independent directions and still accused a real writer. A non-native
or rubric-driven writer whose careful, formal prose reads as "predictable" to
GPT-2 and "even" to the stylometer is exactly the person my README's
false-positive trace is about, and this row is that person being labelled
high-confidence AI with an appeal link as their only recourse.



---

## Run Log and Verdicts


| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing is rarely called AI | At most 1 of 10 human pieces gets `"ai"` | 7 of 10 `"ai"` (all 3 plain L2 pieces among them) | 7 of 10 `"ai"` | 7 of 10 `"ai"` | **Not met** |
| 2. Score spread | Zero overlap (lowest AI > highest human) and AI mean ≥ human mean + 0.25 | Overlap: lowest AI 0.633 < highest human 0.733. Means 0.724 vs 0.690, gap 0.034 | Same | Same | **Not met** |
| 3. Label coverage | ≥ 1 human gets `"human"`, ≥ 1 AI gets `"ai"`, ≥ 2 of 5 borderline get `"unsure"` | Human 0 of 2 (unsure, ai); AI 1 of 2; borderline 1 of 5 | Same | Same | **Not met** |
| 4. Appeal path | 3 real ids → `200 under_review`, appeal logged, original unchanged; 3 fake ids → `404`; missing `reasoning` → `400` | Checked once by hand, not part of the three trials | — | — | **Appeal half met; 404/400 to confirm** |
| 5. Bad input | Every bad request → `400`, never `500` | 7 of 7 → `400` | 7 of 7 → `400` | 7 of 7 → `400` | **Met** |

Notes on the evidence:

- **Criterion 2** uses the score-spread scenario: the first five texts are the
  GPT-4o group (0.6328, 0.7815, 0.7553, 0.6400, 0.8094) and the last five are
  mine (0.7245, 0.7065, 0.7334, 0.5874, 0.6959). Two AI texts score below four
  of my five human texts.
- **Criterion 3**: the scenario uses 2 human texts, 2 AI texts and 5 borderline
  texts, not the full 5 + 5 that `criteria.md` describes. Neither human text
  reached `"human"` (0.6055 unsure, 0.7195 ai). Only borderline 1 (0.6335)
  came back `"unsure"`; the other four came back `"ai"`.
- **Criterion 4**: `logs/audit.jsonl` shows three real `content_id`s appealed on
  2026-11-02 (`3094e770…`, `e8f10c9a…`, `e412ee07…`), each with
  `status: "under_review"`, and each original `"decided"` entry still present
  with the same `guess`, score and timestamp. The `404` and `400` responses
  are not written to the log, so they need their own curl output as evidence.
- **Criterion 5**: the eval sends 7 of the 8 cases. Case (f), a JSON list body,
  is covered by attack RQ07 in the attack run above, which also got `400`.
- An earlier run at 13:38 is not used: its third trial hit my own 5-per-minute
  limit and every request came back `429`.

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

Criterion 1, trial 1, from `results/run_2026-11-07_1335_before.md`, produced by
`run_eval.py::main` against `app.py::submit`:

```json
[
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8316,
    "model_score": 0.8631,
    "style_score": 0.8,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 5de6f270-b7eb-4171-9c45-f50c088c8a3b.",
    "sent": "I go to the market every Saturday morning. I buy fruit and vegetables "
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8262,
    "model_score": 0.8517,
    "style_score": 0.8008,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number f8de6b59-4403-4180-b302-03f18f4a95aa.",
    "sent": "My sister lives in a small town near the sea. She works in a bakery. E"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8481,
    "model_score": 0.8486,
    "style_score": 0.8476,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 8de91e75-8cf2-4c53-9b78-b2ef75274dbf.",
    "sent": "Last weekend I cleaned my room. I put all my books on the shelf. I was"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.6055,
    "model_score": 0.6586,
    "style_score": 0.5524,
    "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.",
    "sent": "I walked to the corner store this morning. The owner was out front, sw"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.55,
    "model_score": 0.4214,
    "style_score": 0.6787,
    "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.",
    "sent": "The library near my apartment has a reading room with tall windows. I "
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.7195,
    "model_score": 0.6775,
    "style_score": 0.7615,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 60282565-53df-4fda-9b53-b5ecee93be01.",
    "sent": "My grandfather kept a notebook of every bird he saw from his kitchen w"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8126,
    "model_score": 0.7089,
    "style_score": 0.9163,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 17da04bb-afb5-4b9e-a26f-7721956fd15e.",
    "sent": "There is a bench at the top of the hill behind our school. You can see"
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.8424,
    "model_score": 0.797,
    "style_score": 0.8877,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 7502400e-20ba-4f64-b917-88d5354fa131.",
    "sent": "I tried to cook a new recipe last night. It was a simple pasta dish wi"
  },
  {
    "status": 200,
    "guess": "unsure",
    "confidence": 0.426,
    "model_score": 0.4206,
    "style_score": 0.4314,
    "label": "We're not sure whether this was written by a person or an AI. Our checks didn't give a clear answer, so we're not making a call either way.",
    "sent": "The train was late again this morning, so I stood on the platform and "
  },
  {
    "status": 200,
    "guess": "ai",
    "confidence": 0.6505,
    "model_score": 0.6474,
    "style_score": 0.6537,
    "label": "Our checks suggest this was probably written by an AI. If that's wrong, you can appeal this decision using reference number 6b027aa1-6244-479f-8fac-0183de80ee40.",
    "sent": "My neighbour has a dog that barks at everything. At first it annoyed m"
  }
]
```

**Diagnoses**

### Verdicts

| Criterion | Target | Verdict | Evidence |
|---|---|---|---|
| 1. my own writing not flagged as AI | ≤ 1/10 | **MISSED** | 7 of 10 labelled "ai" in all three trials |
| 2. score spread | AI mean − human mean ≥ 0.25 | **MISSED** | 0.724 vs 0.690, gap ≈ 0.03 |
| 3. all three labels reachable | 3/3 | **MISSED** | only "ai" and "unsure"; no "human" in any trial |
| 4. appeal always changes status | 5/5 | 1/1 (by hand) | **MET**|
| 5. bad input returns 400, never 500 | 7/7 | **MET** | 7 of 7 returned 400 in all three trials |



Miss 1 — criterion 1 (7 of 10 of my own pieces labelled "ai")
Stage: signal one, with signal two agreeing. Mechanism: the model signal
scores my plain, second-language-style writing between 0.65 and 0.86, because
short common sentences are easy for GPT-2 to predict. Signal two agrees, scoring
the same pieces 0.55–0.92, because evenly sized sentences and a narrow
vocabulary look "regular". Both signals are above AI_FLOOR (0.6), so the
agreement rule in combine_signals never fires and the combined score lands at
0.65–0.85 — well above AI_THRESHOLD (0.65). This is the exact false-positive
case my design note warned about: plain writing is the model signal's blind
spot, formal/even structure is the style signal's blind spot, and my test pieces
hit both at once.

Miss 2 — criterion 2 (spread ≈ 0.034, not 0.25)
Stage: combining rule plus thresholds, caused by both signals. Mechanism:
the AI group's mean combined score is 0.724 and the human group's is 0.690 — a
gap of about 0.034, an order of magnitude short of 0.25 — and the groups overlap
badly (the human water-bottle text scores 0.7245, higher than the AI water-bottle
text at 0.6328). The cause is the same as Miss 1: my human texts score high on
both signals, so no rule that only averages or gates these two numbers can pull
them apart. The rule is not faulty; its inputs are not separated.

Miss 3 — criterion 3 (no "human" verdict)
Stage: label mapping plus thresholds, rooted in signal one. Mechanism:
score_to_label maps score <= 0.35 to "human", but the lowest combined score
any human text reached was 0.426, and the model signal alone never went below
0.42 on real writing. The "human" band at 0.00–0.35 is therefore unreachable in
practice: the model signal's floor on human prose sits above the band's ceiling.
This is a threshold/calibration problem, not a bug — but as written the criterion
cannot pass.

Pattern across the misses
Three of the misses and the false-positive attacks are one problem, not four:
the model signal scores ordinary human writing too high, and the style signal
scores even, formal human writing too high. Because both signals lean AI on
human text, the combining rule has nothing to separate, the "human" band is
unreachable, and the spread collapses. The highest-leverage fix is signal
one's calibration on human prose (or a wider unsure band and a higher
HUMAN_THRESHOLD), not tuning combine_signals, which is behaving as designed.



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
