"""
Turning two numbers into one, and one number into something a person can read.
← YOU BUILD THIS IN MILESTONES 4 AND 5

Two functions live here, and both are stubs.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import config


def combine_signals(model_score: float, style_score: float) -> float:
    """
    Combine two 0–1 signals into one 0–1 score. Higher means more likely AI.

    Args:
        model_score: from `detector.model_signal` — how predictable the text is.
        style_score: from `stylometry.style_signal` — the shape of the text.

    Returns:
        A float from 0.0 (confidently human) to 1.0 (confidently AI).

    The rule — a weighted average plus an agreement rule. A confident label
    needs both signals on the same side:

      1. Weighted average (WEIGHT_MODEL_SIGNAL / WEIGHT_STYLE_SIGNAL, 0.5 each).
      2. If either signal is below AI_FLOOR (0.6), cap at UNSURE_CAP (0.74):
         "unsure" at worst, never "ai". One signal can't convict on its own.
      3. If either signal is above HUMAN_CEILING (0.5), raise to HUMAN_FLOOR
         (0.36): "unsure" at best, never "human".

    When the signals split, both apply and the score is held inside the unsure
    band — disagreement always means "unsure". The AI side asks for stronger
    agreement (0.6) than the human side (0.5) because a wrong accusation costs
    the writer more than a missed detection costs the site.

    The split case that shaped it: the opening of Walden scored 0.758 on the
    model signal (GPT-2 has likely seen it) and 0.009 on style. A plain average
    says 0.384; this rule says the same number, but guarantees it stays in
    "unsure" whatever the thresholds become. All numbers are in config.py.
    """
    combined = (
        config.WEIGHT_MODEL_SIGNAL * model_score
        + config.WEIGHT_STYLE_SIGNAL * style_score
    )

    if min(model_score, style_score) < config.AI_FLOOR:
        combined = min(combined, config.UNSURE_CAP)

    if max(model_score, style_score) > config.HUMAN_CEILING:
        combined = max(combined, config.HUMAN_FLOOR)

    return round(combined, 4)


def score_to_label(score: float, content_id: str | None = None) -> tuple[str, str]:
    """
    Turn a score into a guess and the text a reader actually sees.

    Args:
        score:      the combined score, 0.0 (human) to 1.0 (AI).
        content_id: the submission's id. The "ai" label quotes it so the writer
                    has what they need to appeal. Optional, so a caller that
                    only wants the guess can leave it out.

    Ranges (thresholds in config.py):
        score <= HUMAN_THRESHOLD (0.35)  -> "human"
        score >= AI_THRESHOLD    (0.75)  -> "ai"
        anything between                 -> "unsure"

    Returns:
        (guess, label_text) — where `guess` is a short machine-readable string
        like "ai" / "human" / "unsure", and `label_text` is the full sentence
        shown to a person.

    ⚠️ Write the label text for someone who has never heard the word
    "threshold".

        ✗ "human, 0.81 confidence"
        ✓ "We think this was probably written by a person."

    All three labels have to be **reachable**. If no score can produce one of
    them, your ranges have a gap — and Milestone 5 asks you to submit text that
    produces each one, which is how you'd find out.

    The hardest one to write is "unsure". It has to admit uncertainty without
    sounding like an accusation, because the person reading it may well have
    written every word themselves. Your breakout asks your group what they'd
    think if they got it on their own work. That question is the whole
    milestone.
    """
    if score >= config.AI_THRESHOLD:
        if content_id:
            appeal = f"you can appeal this decision using reference number {content_id}."
        else:
            appeal = "you can appeal this decision."
        return "ai", (
            "Our checks suggest this was probably written by an AI. "
            f"If that's wrong, {appeal}"
        )
    if score <= config.HUMAN_THRESHOLD:
        return "human", "We think this was probably written by a person."
    return "unsure", (
        "We're not sure whether this was written by a person or an AI. "
        "Our checks didn't give a clear answer, so we're not making a call either way."
    )


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} – {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00"),
    ]
