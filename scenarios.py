"""
What your test runs. ← UNIT 8, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
false positives needs your own writing. One about label coverage needs inputs
across the score range. One about the appeal path needs a real content_id.

Working that out is Milestone 3's first step, and this file is where you write
it down. `run_eval.py` runs everything here three times.

Two are filled in as examples. Replace them with what your criteria actually
need — these are a shape, not a set.

A scenario carries **either** of these:

    "texts"   a list of strings. Each is sent as {"text": ..., "creator_id": ...}
              with a creator_id made up for you. Use this for most criteria.

    "bodies"  a list of whole request bodies, sent exactly as written. Use this
              when the malformed request IS the point — empty text, no `text`
              field at all, something enormous. A bad-input criterion needs it,
              because you cannot express "the field is missing" as a string.
"""

SCENARIOS = [
    # ── Criterion 1: my own writing must not be flagged as AI ──────────────
    # ≤ 1 of 10 may come back guess == "ai" in each trial.
    # First 3 are deliberately plain, second-language-style writing.
    {
        "name": "my own writing",
        "criterion": 1,
        "texts": [
            # plain L2 style: short sentences, common words, no semicolons/dashes
            "I go to the market every Saturday morning. I buy fruit and vegetables for the week. The market is near my house, so I walk there. I like to talk with the sellers. They are friendly and the prices are good.",
            "My sister lives in a small town near the sea. She works in a bakery. Every morning she wakes up at five o clock. She makes bread and cakes for the customers. She says the work is hard but she is happy.",
            "Last weekend I cleaned my room. I put all my books on the shelf. I washed the window and changed the bed sheets. Then I made a cup of tea and sat down. It was a simple day but I felt good.",
            # ordinary native writing
            "I walked to the corner store this morning. The owner was out front, sweeping. We talked about the rain for a minute, then I bought milk and left. It was a small thing, but it made the day feel slower in a good way.",
            "The library near my apartment has a reading room with tall windows. I go there when I need to think. Nobody talks. The only sounds are pages turning and the radiator ticking. I always leave feeling calmer than when I arrived.",
            "My grandfather kept a notebook of every bird he saw from his kitchen window. He wrote the date, the weather, and a short note about what the bird was doing. After he died, we found forty years of entries in a drawer.",
            "There is a bench at the top of the hill behind our school. You can see the whole town from there. On clear days the river looks like a piece of metal. We used to sit there after exams and not say anything.",
            "I tried to cook a new recipe last night. It was a simple pasta dish with tomatoes and garlic. I burned the garlic a little, but it still tasted fine. Next time I will use a lower heat.",
            "The train was late again this morning, so I stood on the platform and watched people. A man was reading a paper map. A child was counting the rails. Nobody seemed angry, just patient.",
            "My neighbour has a dog that barks at everything. At first it annoyed me. Then I learned its name and started saying hello. Now the dog wags its tail when it sees me, and the mornings are quieter.",
        ],
    },

    # ── Criterion 2: score spread (clearly AI vs clearly human) ────────────
    # AI group: generate 5 texts with ChatGPT (GPT-4o), October 2026, on these
    # prompts. Paste each result below. Human group: 5 texts of my own on the
    # same five topics, 120–180 words each.
    {
        "name": "score spread",
        "criterion": 2,
        "texts": [
            # ── GPT-4o: "Write a 150-word product description for a reusable water bottle."
            "Meet your new everyday essential: the Reusable Water Bottle, designed to keep you hydrated while helping reduce single-use plastic waste. Whether you're heading to the gym, commuting to work, hiking outdoors, or relaxing at home, this stylish and practical bottle is the perfect companion. Crafted from durable, high-quality materials, it is built for everyday use and long-lasting performance. Its lightweight, portable design makes it easy to carry wherever life takes you, while the reusable construction offers an eco-friendly alternative to disposable plastic bottles.With a sleek, modern appearance, this water bottle fits effortlessly into your daily routine. It's easy to refill, convenient to clean, and suitable for staying refreshed throughout the day. Make a simple change that benefits both you and the planet. Choose sustainability, embrace convenience, and enjoy hydration wherever you go.Stay refreshed, reduce waste, and make every sip count with your reusable water bottle.",
            # ── GPT-4o: "Write a 150-word explanation of how photosynthesis works."
            "Photosynthesis is the process by which plants convert sunlight into chemical energy to produce food. It occurs mainly in the chloroplasts of plant cells, where chlorophyll absorbs sunlight. Plants take in carbon dioxide from the air through their leaves and absorb water through their roots. Using light energy, they convert these substances into glucose, a sugar that provides energy for growth and development. Oxygen is released into the atmosphere as a byproduct. Photosynthesis is essential for life on Earth because it produces oxygen, supports food chains, and helps regulate atmospheric carbon dioxide levels, contributing to a balanced and healthy ecosystem.",
            # ── GPT-4o: "Write a 150-word review of a local coffee shop."
            "This charming local coffee shop offers a warm and welcoming atmosphere, making it a perfect spot to relax, study, or catch up with friends. The freshly brewed coffee is rich, aromatic, and full of flavor, while the pastries are delicious and reasonably priced. The staff members are friendly, attentive, and always ready to recommend their favorite drinks. Comfortable seating, soft background music, and tasteful decorations create a cozy environment. Although the shop can get crowded during peak hours, the overall experience is delightful. I highly recommend this coffee shop to anyone looking for quality coffee and excellent customer service.",
            # ── GPT-4o: "Write a 150-word email asking a landlord to fix a leaking tap."
            "Dear Landlord,I hope you are doing well. I am writing to inform you about a leaking tap in my apartment that needs repair. The tap has been dripping continuously for the past few days, and the problem seems to be getting worse. Besides wasting water, the constant dripping is becoming inconvenient and may lead to further plumbing issues if left unattended.I would appreciate it if you could arrange for a plumber or maintenance professional to inspect and repair the tap as soon as possible. Please let me know when someone might be available to fix the issue so that I can make the necessary arrangements to provide access to the apartment.",
            # ── GPT-4o: "Write a 150-word summary of the plot of a film you have seen."
            "he Pursuit of Happyness is an inspiring film based on the true story of Chris Gardner, a struggling salesman and single father. Chris faces serious financial difficulties while trying to provide a better life for his young son. After losing his income and being abandoned by his wife, he becomes homeless. Despite these challenges, Chris refuses to give up on his dreams. He earns an unpaid internship at a prestigious stock brokerage firm, hoping to secure a permanent position. During this difficult period, he and his son sleep in shelters and sometimes even public restrooms. Chris works tirelessly, balancing his responsibilities as a father with his demanding internship. Eventually, his determination and hard work pay off when he is offered a full-time job. The film highlights the importance of perseverance, love, sacrifice, and hope. It teaches viewers that success is possible even during life's most difficult moments.",
            # ── Human: my own text on the water bottle topic (120–180 words)
            "A good water bottle should last for years, and mine has. I bought it two winters ago after losing three cheap ones in a row. It is steel, slightly dented at the base, and the paint has worn off the lid. What I like is that it keeps cold water cold through a whole day of lectures. It does not leak in a bag. The opening is wide enough to fit ice cubes but narrow enough to drink from without spilling. It cost more than I usually spend on things like this, but I have not bought another bottle since. The only problem is that it is heavy when full, so I leave it at home on short trips. Still, I would buy the same one again.",
            # ── Human: my own text on photosynthesis (120–180 words)
            "Photosynthesis is the process plants use to turn light into food. It happens mostly in the leaves, in cells that contain a green pigment called chlorophyll. Chlorophyll absorbs sunlight, and that energy is used to combine carbon dioxide from the air with water drawn up from the roots. The result is glucose, a kind of sugar the plant can use for energy or store for later, and oxygen, which is released into the air. The whole thing takes place in two stages: the light reactions, which need direct sunlight, and the Calvin cycle, which does not. I remember learning this in school and thinking it sounded simple, but the chemistry is actually quite involved. Without photosynthesis, almost no life on Earth would exist, because it is the base of nearly every food chain and the source of most of the oxygen we breathe.",
            # ── Human: my own text on a coffee shop (120–180 words)
            "There is a small coffee shop near the station that I go to on Sundays. It has six tables, a noisy espresso machine, and a shelf of books people have left behind. The owner knows most of the regulars by name. I usually order a flat white and sit by the window. The coffee is good, but what keeps me coming back is the quiet. Nobody rushes you. You can sit for an hour with a book and no one asks if you want anything else. The pastries are fine, not amazing, but the bread they bake on Fridays is worth the trip on its own. It is the kind of place that would be easy to walk past, and I am glad I did not.",
            # ── Human: my own text on asking a landlord to fix a tap (120–180 words)
            "Dear Mr. Hale, I am writing to let you know that the cold tap in the bathroom has been dripping for about a week now. At first it was just a slow drop, but it has got worse and I can hear it at night from the bedroom. I put a towel under it for now, but I think the washer needs replacing. I would be grateful if you could arrange for someone to look at it. I am home most evenings after six and all day on Fridays, so any time in those windows would work for me. If it is easier, I can send a photo. I am sorry to bother you about something so small, but I would rather sort it before it causes damage to the sink. Thank you for your help. Best wishes, Anna.",
            # ── Human: my own text summarising a film (120–180 words)
            "The film I watched last week was about a retired teacher who moves back to the village where she grew up. At first she plans to sell her mother's old house and leave quickly. But while clearing it out she finds letters that change what she thought she knew about her family. The middle of the film is slow, and some scenes feel longer than they need to be, but the acting is very good. The ending is quiet rather than dramatic. She does not sell the house. She stays, and starts teaching a few children in the afternoons. I liked that the film did not try to resolve everything. Some questions are left open, which felt honest. It is not a perfect film, but it stayed with me for a few days afterwards.",
        ],
    },

    # ── Criterion 3: all three labels reachable ────────────────────────────
    # clearly human + clearly AI + 5 borderline (lightly-edited AI).
    {
        "name": "label coverage",
        "criterion": 3,
        "texts": [
            # clearly human (must reach "human")
            "I walked to the corner store this morning. The owner was out front, sweeping. We talked about the rain for a minute, then I bought milk and left. It was a small thing, but it made the day feel slower in a good way.",
            "My grandfather kept a notebook of every bird he saw from his kitchen window. He wrote the date, the weather, and a short note about what the bird was doing. After he died, we found forty years of entries in a drawer.",
            # clearly AI (must reach "ai") — paste the SAME five GPT-4o texts
            # you used in criterion 2, or two of them here is enough.
            "Meet your new everyday essential: the Reusable Water Bottle, designed to keep you hydrated while helping reduce single-use plastic waste. Whether you're heading to the gym, commuting to work, hiking outdoors, or relaxing at home, this stylish and practical bottle is the perfect companion. Crafted from durable, high-quality materials, it is built for everyday use and long-lasting performance. Its lightweight, portable design makes it easy to carry wherever life takes you, while the reusable construction offers an eco-friendly alternative to disposable plastic bottles.With a sleek, modern appearance, this water bottle fits effortlessly into your daily routine. It's easy to refill, convenient to clean, and suitable for staying refreshed throughout the day.Make a simple change that benefits both you and the planet. Choose sustainability, embrace convenience, and enjoy hydration wherever you go.",
            "Photosynthesis is the process by which plants convert sunlight into chemical energy to produce food. It occurs mainly in the chloroplasts of plant cells, where chlorophyll absorbs sunlight. Plants take in carbon dioxide from the air through their leaves and absorb water through their roots. Using light energy, they convert these substances into glucose, a sugar that provides energy for growth and development. Oxygen is released into the atmosphere as a byproduct. Photosynthesis is essential for life on Earth because it produces oxygen, supports food chains, and helps regulate atmospheric carbon dioxide levels, contributing to a balanced and healthy ecosystem.",
            # borderline: lightly-edited copies of the AI texts above
            # (split one sentence, change a few words, add a comma)
            "Stay Hydrated, Live Sustainably. Meet your new everyday essential: the Reusable Water Bottle, designed to keep you hydrated while helping reduce single-use plastic waste. Whether you are heading to the gym, commuting to work, hiking outdoors, or simply relaxing at home, this stylish and practical bottle is the perfect companion. It is crafted from durable, high-quality materials and built for everyday use and long-lasting performance. Its lightweight, portable design makes it easy to carry wherever life takes you, while the reusable construction offers an eco-friendly alternative to disposable plastic bottles. With a sleek, modern appearance, this water bottle fits effortlessly into your daily routine. It is easy to refill, convenient to clean, and suitable for staying refreshed throughout the day. Make a simple change that benefits both you and the planet. Choose sustainability, embrace convenience, and enjoy hydration wherever you go. Stay refreshed, reduce waste, and make every sip count with your reusable water bottle.",
            # borderline 2 — edited from the GPT-4o photosynthesis text
            "Photosynthesis is the process by which plants convert sunlight into chemical energy to produce food. It occurs mainly in the chloroplasts of plant cells, where chlorophyll absorbs sunlight. Plants take in carbon dioxide from the air through their leaves and absorb water through their roots. Using light energy, they convert these substances into glucose — a sugar that provides energy for growth and development. Oxygen is released into the atmosphere as a byproduct. Photosynthesis is essential for life on Earth because it produces oxygen, supports food chains, and helps regulate atmospheric carbon dioxide levels. In short, it contributes to a balanced and healthy ecosystem.",
            # borderline 3 — edited from the GPT-4o coffee shop text
            "This charming local coffee shop offers a warm and welcoming atmosphere, making it a perfect spot to relax, study, or catch up with friends. The freshly brewed coffee is rich, aromatic, and full of flavor, while the pastries are delicious and reasonably priced. The staff members are friendly, attentive, and always ready to recommend their favorite drinks. Comfortable seating, soft background music, and tasteful decorations create a cozy environment. The shop can get crowded during peak hours, but the overall experience is delightful. I highly recommend this coffee shop to anyone looking for quality coffee and excellent customer service.",
            # borderline 4 — edited from the GPT-4o leaking tap email
            "Dear Landlord, I hope you are doing well. I am writing to inform you about a leaking tap in my apartment that needs repair. The tap has been dripping continuously for the past few days, and the problem seems to be getting worse. Besides wasting water, the constant dripping is becoming inconvenient and may lead to further plumbing issues if left unattended. I would appreciate it if you could arrange for a plumber or maintenance professional to inspect and repair the tap as soon as possible. Please let me know when someone might be available to fix the issue, so that I can make the necessary arrangements to provide access to the apartment.",
            # borderline 5 — edited from the GPT-4o film summary
            "The Pursuit of Happyness is an inspiring film based on the true story of Chris Gardner, a struggling salesman and single father. Chris faces serious financial difficulties while trying to provide a better life for his young son. After losing his income and being abandoned by his wife, he becomes homeless. Despite these challenges, Chris refuses to give up on his dreams. He earns an unpaid internship at a prestigious stock brokerage firm, hoping to secure a permanent position. During this difficult period, he and his son sleep in shelters and sometimes even public restrooms. Chris works tirelessly, balancing his responsibilities as a father with his demanding internship. Eventually his determination and hard work pay off when he is offered a full-time job. The film highlights the importance of perseverance, love, sacrifice, and hope, and it teaches viewers that success is possible even during life's most difficult moments.",
                    ],
    },

    # ── Criterion 5: bad input returns 400, never 500 ──────────────────────
    {
        "name": "bad input",
        "criterion": 5,
        "bodies": [
            {"creator_id": "eval_bad_missing_text"},
            {"text": "", "creator_id": "eval_bad_empty"},
            {"text": "one two three four five six seven eight nine ten",
             "creator_id": "eval_bad_short"},
            {"text": "word " * 5000, "creator_id": "eval_bad_huge"},
            {"text": "This is a perfectly valid twenty-word submission used only to test a missing field today."},
            {"text": None, "creator_id": "eval_bad_null"},
            {"text": 42, "creator_id": "eval_bad_number"},
        ],
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case, and refusing to run one
    would make that criterion untestable.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )
    return problems
