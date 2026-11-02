"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── Calibration — the one place to tune ──────────────────────────────────────
# Each measure gets two anchors: the raw value that counts as AI-typical (scores
# 1.0) and the one that counts as human-typical (scores 0.0). Anything between
# is linear; anything beyond is clamped. Flipping a measure's direction means
# swapping its two numbers — no code changes.
#
# First calibration: two AI paragraphs, one plain casual paragraph, and the
# opening of Walden. Recalibrate on the four Milestone 4 inputs.

SPREAD_AI, SPREAD_HUMAN = 0.20, 0.70   # AI sentences march in step: low spread = AI
PUNCT_AI, PUNCT_HUMAN = 0.04, 0.12     # AI uses fewer commas/semicolons/dashes per word
TTR_AI, TTR_HUMAN = 0.90, 0.75         # weakest measure: AI scored HIGHER vocab variety
                                       # than the human text, opposite to the usual claim

WEIGHT_SPREAD, WEIGHT_PUNCT, WEIGHT_TTR = 0.5, 0.3, 0.2

MIN_WORDS = 20      # fewer than this, the whole signal is no evidence (same as /submit)
MIN_SENTENCES = 3   # fewer than this, spread is treated as no evidence
TTR_WINDOW = 50     # words per window for the moving-average type-token ratio


# ── The three measures ───────────────────────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies: the coefficient of variation (standard
    deviation of words-per-sentence divided by the mean), so long and short
    texts are comparable.

    Returns:
        A float >= 0. **Higher means more human** — people put a three-word
        sentence next to a forty-word one; generated prose keeps an even pace.
        Typical: AI 0.2–0.3, varied human writing 0.6 and up.

    Fewer than two sentences returns 0.0, because `stdev` needs two values.
    That 0.0 is not evidence of anything — `style_signal` treats a text with
    under MIN_SENTENCES sentences as neutral on this measure rather than
    reading it as perfectly even, AI-like rhythm.
    """
    lengths = [len(words(s)) for s in sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return 0.0
    return statistics.stdev(lengths) / statistics.mean(lengths)


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words, as a **moving average**: the ratio inside
    every TTR_WINDOW-word window, averaged. Plain TTR falls as text gets
    longer, so a long text and a short one would differ on length alone;
    fixed-size windows remove that. Texts shorter than one window use plain
    TTR.

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.
        No words returns 0.0.

    Direction is the open question. The usual claim is that AI vocabulary is
    narrower, but in first calibration the AI paragraphs scored higher than
    human writing — modern models reach for varied words. That is why it has
    the lowest weight, and why its anchors run high = AI.
    """
    ws = words(text)
    if not ws:
        return 0.0
    if len(ws) < TTR_WINDOW:
        return len(set(ws)) / len(ws)
    windows = range(len(ws) - TTR_WINDOW + 1)
    return statistics.mean(len(set(ws[i:i + TTR_WINDOW])) / TTR_WINDOW for i in windows)


_MARKS = re.compile(r'--|[,;:()!?"—–]')


def punctuation_density(text: str) -> float:
    """
    Punctuation marks per word, counting only the marks that vary between
    writers: commas, semicolons, colons, brackets, ! and ?, double quotes, and
    dashes (em, en, and "--"). Full stops are left out — every sentence has one,
    so they measure sentence count, not style.

    Returns:
        A float >= 0. **Higher means more human.** Typical: AI around 0.04–0.06,
        comma-heavy human prose 0.12 and up. No words returns 0.0.

    Known weakness: ChatGPT is fond of em dashes, which pushes it toward
    "human" here. Check this against the GPT texts in criterion 2.
    """
    ws = words(text)
    if not ws:
        return 0.0
    return len(_MARKS.findall(text)) / len(ws)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.** ← TODO

    Combine your three measures into one number. Same direction as
    `detector.model_signal`, so that `scoring.combine_signals` can treat them
    the same way — if one of your signals runs backwards, everything above it
    is wrong in a way that's hard to see.

    Two things to decide and write down:

      1. Which direction each measure points. Low spread means more AI-ish, so
         it needs flipping. Work out which of your three need that.
      2. How to get each onto a comparable scale. A raw type-token ratio sits
         between 0 and 1; a raw punctuation count doesn't. Adding them
         unscaled means whichever has the bigger numbers wins by default.

    Test it on the four calibration inputs from Milestone 4 — clearly AI,
    clearly human, plain conventional human writing, lightly-edited AI — before
    you trust it. Plain and ordinary, not formal: formal prose reads as *human*
    to signal one, and it is plain writing that gets accused.

    How it's built: each measure is scaled between its two anchors (see the
    calibration block at the top), so all three sit on the same 0–1 scale and
    point the same way, then they are averaged with weights 0.5 / 0.3 / 0.2 —
    spread counts most because it separated AI from human most clearly in
    calibration; TTR least because it barely separated them at all.
    """
    if len(words(text)) < MIN_WORDS:
        # A handful of words has every word unique and no commas, which reads
        # as "AI" on two measures for no real reason. Too little to judge.
        return 0.5

    spread_ai = _scale(sentence_length_spread(text), SPREAD_AI, SPREAD_HUMAN)
    if len(sentences(text)) < MIN_SENTENCES:
        # Too few sentences to judge rhythm. Neutral, not "perfectly even".
        spread_ai = 0.5
    punct_ai = _scale(punctuation_density(text), PUNCT_AI, PUNCT_HUMAN)
    ttr_ai = _scale(type_token_ratio(text), TTR_AI, TTR_HUMAN)

    score = WEIGHT_SPREAD * spread_ai + WEIGHT_PUNCT * punct_ai + WEIGHT_TTR * ttr_ai
    return round(score, 4)


def _scale(raw: float, ai_anchor: float, human_anchor: float) -> float:
    """
    Map a raw measure onto 0–1, where the AI anchor scores 1.0 and the human
    anchor scores 0.0. Works whichever way round the anchors are, which is what
    lets a measure's direction be flipped by swapping two numbers.
    """
    value = (raw - human_anchor) / (ai_anchor - human_anchor)
    return min(max(value, 0.0), 1.0)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text):.3f}   (higher = more human)")
    print(f"type_token_ratio         {type_token_ratio(text):.3f}   (moving average)")
    print(f"punctuation_density      {punctuation_density(text):.3f}   (higher = more human)")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
