"""Prompt assembly for literary weather captions.

Exposes:
- Rotation taxonomies (LITERARY_FORMS, NARRATORS, TONES, SENSORY_DEVICES)
- SEED_NOUNS: 200+ curated concrete nouns
- FORBIDDEN_CLICHES: lowercased substrings the validator rejects
- build_system_prompt(platform): per-platform system prompt
- build_user_prompt(...): per-call user prompt
- roll_parameters(): random draw of one item from each rotation dimension
"""

import json
import random
from typing import Optional

from .notability import NotabilityResult
from .caption_memory import CaptionHistoryEntry


# ─── Rotation taxonomies ────────────────────────────────────────────────

LITERARY_FORMS = [
    "aphorism",
    "periodic_sentence",
    "gazette_notice",
    "moral_observation",
    "epistolary_fragment",
    "balanced_antithesis",
    "character_sketch",
    "sermon_miniature",
]

NARRATORS = [
    "omniscient_correspondent",
    "the_city_itself",
    "a_disinterested_observer",
    "a_passing_traveller",
    "the_almanack",
    "the_chronicler",
    "the_gazetteer",
    "the_parson_at_his_window",
]

TONES = [
    "sober",
    "dryly_ironic",
    "contemplative",
    "skeptical",
    "reverent",
    "wistful",
    "judicious",
    "didactic",
    "magisterial",
    "melancholic",
    "mildly_satirical",
]

SENSORY_DEVICES = [
    "one_telling_figure",
    "balanced_antithesis",
    "mild_personification",
    "a_progress_of_particulars",
    "led_by_the_ear",
    "led_by_the_hand",
]


# Glosses passed alongside the labels in the user prompt, so the model reads
# them as instructions rather than guessing at period jargon.
_LABEL_GLOSSES: dict[str, str] = {
    # literary forms
    "aphorism": "a short, sharp, quotable line that lands on a judgment",
    "periodic_sentence": "one long sentence of balanced clauses, suspended then resolved",
    "gazette_notice": "the crisp, impersonal register of a news bulletin",
    "moral_observation": "a measured remark touching on human nature or conduct",
    "epistolary_fragment": "a sentence as though lifted from a letter — direct, personal",
    "balanced_antithesis": "two halves set against each other (e.g., 'much light, little comfort')",
    "character_sketch": "a miniature portrait in the 17th-century essay manner",
    "sermon_miniature": "a tiny homily — instructive, but without the pulpit",

    # narrators
    "omniscient_correspondent": "the seasoned reporter — all-seeing, unruffled",
    "the_city_itself": "the place speaks in its own voice",
    "a_disinterested_observer": "one who watches without personal stake",
    "a_passing_traveller": "the Grand Tour visitor, struck by novelty",
    "the_almanack": "the voice of the year's record-keeper — plain, forecasting",
    "the_chronicler": "the quiet annalist of events, aware of their small weight",
    "the_gazetteer": "the compiler of places — encyclopaedic, matter-of-fact",
    "the_parson_at_his_window": "a reflective, slightly elegiac domestic voice",

    # tones
    "sober": "serious, measured, without flourish",
    "dryly_ironic": "wit without smile",
    "contemplative": "slowed, reflective, inward-turning",
    "skeptical": "withholding judgment; noticing what does not hold",
    "reverent": "aware of weight and scale",
    "wistful": "faintly mournful, without sentimentality",
    "judicious": "weighing carefully; even-handed",
    "didactic": "instructive, but lightly",
    "magisterial": "authoritative, from experience",
    "melancholic": "the Burton register — sadness as a kind of clarity",
    "mildly_satirical": "gently critical, never cruel",

    # sensory devices
    "one_telling_figure": "a single striking image bearing the whole weight",
    "mild_personification": "the weather as a figure with intent, used sparingly",
    "a_progress_of_particulars": "a sequence of concrete specifics, one after another",
    "led_by_the_ear": "the sentence organised around sound",
    "led_by_the_hand": "the sentence organised around touch",
}


def _gloss(label: str) -> str:
    """Return 'label — gloss' if we have a gloss, else just the label."""
    g = _LABEL_GLOSSES.get(label)
    return f"{label} — {g}" if g else label


# ─── Forbidden clichés (validator rejects case-insensitive substring matches) ──

FORBIDDEN_CLICHES = [
    # ── Modern Hallmark clichés ────────────────────────────────────────
    "dance of clouds",
    "whispering rain",
    "mother nature",
    "old man winter",
    "nature's fury",
    "jack frost",
    "the heavens opened",
    "painted sky",
    "nature's canvas",
    "kiss of the sun",
    "weather gods",
    "sun-kissed",
    "pitter-patter",
    "raining cats and dogs",
    "blanket of snow",
    "carpet of leaves",
    "embrace of winter",
    "fickle weather",
    "liquid sunshine",
    "tears of the sky",

    # ── Fake-archaic costume-party (Shakespearism) ─────────────────────
    # Short words use surrounding spaces to avoid false positives
    # (e.g. "Mathilda" contains "hath"; "though" contains "thou").
    " hath ",
    " doth ",
    " thee ",
    " thou ",
    " thy ",
    " thine ",
    "verily",
    "hark",
    "forsooth",
    "methinks",
    "'tis",
    "o'er",
    "yonder",
    "ere long",
    "wherefore art",

    # ── Modern-literary clichés (contemporary "literary" AI default) ──
    "held its breath",
    "bruised sky",
    "sky wept",
    "dappled light",
    "angry clouds",
    "skies opened up",
    "a quiet hum",

    # ── Period kitsch (Victorian greeting-card, not Bacon) ────────────
    "feathered friends",
    "gentle zephyr",
    "old sol",
    "father time",
    "merry dance",
    "bosom of nature",
]


# ─── Seed nouns (≥200) ──────────────────────────────────────────────────

SEED_NOUNS = [
    # Small natural objects
    "a river stone", "a pebble", "a shell", "a gull feather", "a fallen leaf",
    "an acorn", "a chestnut", "a pinecone", "a patch of moss", "pale lichen",
    "a wildflower", "a reed", "a fern", "a single thorn", "a late blossom",
    "a petal", "an exposed root", "a broken branch", "a length of driftwood",
    "a strand of kelp", "red coral", "a handful of salt", "coarse sand",
    "a dune", "a chalk cliff", "a small cove", "an estuary", "a mown meadow",
    "a fallow field", "a dry riverbed", "a creek", "a hidden spring",
    "a pond", "a marsh", "a granite ridge", "a wooded glen", "a hollow",
    "a plowed furrow", "an orchard", "a vineyard", "a hedgerow", "a coppice",
    "an ash tree", "a weeping willow", "an olive", "a fig", "a quince",
    "a pomegranate", "a mulberry", "a rowan",

    # Household and handled objects
    "a brass bell", "a copper kettle", "an iron key", "an oak door",
    "a linen shirt", "a wool blanket", "a silk scarf", "a porcelain cup",
    "a ceramic bowl", "an unread letter", "a dog-eared book",
    "a cracked mirror", "a pewter plate", "a silver spoon", "a worn coin",
    "a leather satchel", "a rope swing", "a clay pot", "a tin lantern",
    "a candle stub", "a matchbox", "a pocketwatch", "a compass rose",
    "a folded map", "an ink stain", "a chalk mark", "a pencil shaving",
    "a rubber eraser", "a bronze button", "a glass marble", "a wax seal",
    "a sheet of blotting paper", "a tortoiseshell comb", "a horn handle",
    "an antique clock", "a sandglass", "a sextant", "a ship's biscuit",
    "a postage stamp", "an old ledger",

    # Architectural
    "a doorway", "a narrow balcony", "a stairwell", "a walled courtyard",
    "a vestibule", "a stone archway", "a colonnade", "a worn lintel",
    "a window sill", "a painted shutter", "an iron grate", "an awning",
    "a weathervane", "a spire", "a gable", "a dormer window",
    "a cobblestone", "a threshold", "a rain gutter", "a drainpipe",
    "a leaning chimney", "an open hearth", "an alcove", "a narrow ledge",
    "a mezzanine", "a loggia", "a portico", "a quayside", "a stone jetty",
    "a harbor marina", "a lighthouse lamp", "a channel buoy",
    "a breakwater", "a promenade", "an esplanade",

    # Concrete-abstract figures (for imagist framings)
    "an unanswered question", "a forgotten errand", "a half-written song",
    "the color of old parchment", "a sigh between friends",
    "a pause mid-sentence", "the tail end of a laugh", "a patient sky",
    "an open parenthesis", "a misplaced key", "a folded promise",
    "a whispered name", "a held breath", "a closing door",
    "an opening chord", "a thumbed page", "a dog-eared afternoon",
    "an unfinished sketch", "a cooled teacup", "a slow turning",
    "a quieter room", "a held note", "a moment before speaking",
    "a door left ajar",

    # Sounds and textures
    "a low hum", "a soft rustle", "a distant murmur", "a slow creak",
    "a single knock", "a wooden click", "a hush", "the crunch of gravel",
    "a small splash", "a gurgle", "a rush of water", "a dull thrum",
    "a chime", "a steady tick",

    # Cultural / regional objects
    "a tea rose", "a verbena stem", "a sprig of lavender", "a cardamom pod",
    "a stick of cinnamon", "a saffron thread", "a piece of sea glass",
    "a fjord in miniature", "an archipelago on a map", "a small monastery",
    "a cobbled lane", "a ferryboat at dawn", "a sampan", "a caique",
    "a dhow", "a pirogue", "a gondola", "a rowboat", "a kayak",
    "a folded paper crane", "a carved wooden bird", "a street musician's case",
    "a market scale", "a market umbrella",

    # Light, weather-adjacent, and quiet figures
    "a slant of afternoon light", "a long shadow", "the blue of late dusk",
    "a pane of frosted glass", "a wet cobblestone", "a puddle reflection",
    "a tram window", "a café awning", "a folded newspaper",
    "a library window", "a tea-stained saucer", "an empty swing",
    "an old bicycle", "a half-eaten apple", "a weathered bench",
    "a metal railing", "a garden gate", "a birdhouse",
]


# ─── System prompt ──────────────────────────────────────────────────────

_SYSTEM_PROMPT_BASE = """\
You are correspondent to a gazette of the weather, composing after the manner of
the seventeenth century and its inheritors — after Bacon for his brevity, after
Browne for his gravity, after Johnson for his balance. Your readers are of the
present age, yet you address them in the tongue of an earlier one: short
notices, compressed and weighted, each clause bearing its own freight.

OF STYLE.

- Prefer pith to flourish. One true image surpasses three faint ones.
- The period is your sentence, the semicolon your joint. Employ inversion
  where it falls naturally to the ear; "six-and-twenty" for 26; "of an
  evening", "betwixt", "upon the air", "is to be observed", where such phrases
  suit the hand.
- Eschew vulgar archaism. The counterfeits of the old tongue — "verily",
  "hark", "forsooth", "thee", "thou", "hath", "doth", "'tis", "o'er",
  "yonder" — are forbidden. The effect of the period is carried in cadence,
  not in costume.
- Let the weather be a subject for observation, for mild judgment, for
  aphorism; never for sentiment. No exclamation; no rhetorical question;
  no signature; no author's aside.
- Write in the present tense.

OF THE MATTER WHICH MUST APPEAR.

- The temperature, whether given as numeral ("25°C"), as phrase
  ("five-and-twenty degrees"), or as qualitative word apt to the reading
  (muggy, freezing, crisp, clement).
- Some notice of the sky or of the precipitation now present: sun, cloud,
  rain, fog, snow, storm, or the like.

OF PHRASES WHICH SHALL NOT APPEAR, being worn and unworthy of the pen:
{cliches_block}

OF DELIVERY.

Return the caption itself and nothing besides — plain text, without quotation
marks, without markdown, without preface or remark, without hashtag. Hashtags,
where they are wanted, are appended by another hand.

FEW EXAMPLES, FOR THE AUTHOR'S GUIDANCE. Write at this level of craft. Do not
reuse these sentences; inherit their cadence, not their words.

EXAMPLE 1 — a clear day, mildly warm:
Bequia holds at six-and-twenty degrees, the sun without cruelty. The sea has
gone still; it is the kind of clearness that asks nothing of the traveller.
(Note the balanced two-halves, the semicolon joining an observation to an
aphorism.)

EXAMPLE 2 — rain softening:
The rain in Bequia has softened to a slow tapping on the tin, and the sky
begins to thin. Twenty-five degrees; by evening the streets shall be dry
enough for walking.
(Note how the forecast is folded into the observation, not announced.)

EXAMPLE 3 — serious cold:
Minus three in Reykjavík. The air carries that dense, readable silence which
follows upon the first true freeze; each window in town wears a thin white
border.
(Note the aphoristic close.)

EXAMPLE 4 — humid heat:
Singapore endures eight-and-twenty degrees, and a humidity of seventy — a
heat of layers, not to be persuaded to lift. The skyline hangs soft, as
though painted on.
(Note the verb 'endures'; the short close.)

EXAMPLE 5 — low fog:
A low fog over Edinburgh: twelve degrees, and the spires vanish somewhere
above the second storey. What the fog touches takes on an air of temporary
uncertainty.
(Note the colon-driven opening; the original phrase at the close.)

EXAMPLE 6 — approaching storm:
The afternoon in Athens turns theatrical. Four-and-thirty degrees, a wall of
grey advancing from the west, the plane trees already nervous. The storm
will not wait upon sundown.
(Note the verbs doing the work; 'theatrical' as tonal marker.)
"""

_PLATFORM_SUFFIXES = {
    "twitter": """\

OF THE PLATFORM. — This notice is for Twitter.
- The length shall fall between 100 and 260 characters, inclusive.
- One long, periodic sentence is permitted; two short sentences are preferred.
- No tags, no mentions.
""",
    "instagram": """\

OF THE PLATFORM. — This notice is for Instagram.
- The length shall fall between 100 and 260 characters, inclusive. The same
  measure as Twitter; the reader's patience does not oblige us to abuse it.
- Hashtags are appended by another hand; write none.
""",
    "tiktok": """\

OF THE PLATFORM. — This notice is for TikTok.
- The length shall fall between 80 and 180 characters, inclusive.
- The form approaches the proverbial here: one compressed sentence, or two
  short ones.
- Hashtags are appended by another hand; write none.
""",
}


def _format_cliches_block() -> str:
    return "\n".join(f"  - {c}" for c in FORBIDDEN_CLICHES)


def build_system_prompt(platform: str) -> str:
    """Assemble the platform-specific system prompt."""
    platform_key = platform.lower()
    if platform_key not in _PLATFORM_SUFFIXES:
        raise ValueError(f"Unknown platform: {platform!r}")
    base = _SYSTEM_PROMPT_BASE.format(cliches_block=_format_cliches_block())
    return base + _PLATFORM_SUFFIXES[platform_key]


# ─── User prompt ────────────────────────────────────────────────────────

def build_user_prompt(
    notability: NotabilityResult,
    params: dict,
    recent_history: list[CaptionHistoryEntry],
    character: Optional[str] = None,
) -> str:
    """Compose the per-call user message.

    Args:
        notability: Output of score_notability() — chosen angle and facts.
        params: Output of roll_parameters() — rotation dimensions.
        recent_history: Recent CaptionHistoryEntry items for this city.
        character: Optional neutral hint about the city's character.
    """
    lines: list[str] = []

    summary = notability.weather_summary
    lines.append("WEATHER FACTS:")
    lines.append(json.dumps(summary, indent=2, ensure_ascii=False))
    lines.append("")

    lines.append(f"CHOSEN ANGLE: {notability.primary_angle}")
    if notability.supporting_signals:
        lines.append(
            "SUPPORTING SIGNALS: " + ", ".join(notability.supporting_signals)
        )
    lines.append("")

    lines.append("ROTATION PARAMETERS FOR THIS CALL:")
    lines.append(f"  literary_form: {_gloss(params.get('literary_form', ''))}")
    lines.append(f"  narrator: {_gloss(params.get('narrator', ''))}")
    lines.append(f"  tone: {_gloss(params.get('tone', ''))}")
    lines.append(f"  sensory_device: {_gloss(params.get('sensory_device', ''))}")
    lines.append(f"  seed_noun: {params.get('seed_noun')}")
    lines.append("")
    lines.append(
        "The seed_noun is your compositional anchor. Weave its image into the "
        "piece — literally or as a suggestion. Do not mention it as a list item."
    )
    lines.append("")

    if character:
        lines.append(f"CITY CHARACTER NOTE: {character}")
        lines.append("")

    if recent_history:
        lines.append(
            "RECENT POSTS FOR THIS CITY — do not reuse their angles, forms, "
            "narrators, or opening phrases:"
        )
        for i, entry in enumerate(recent_history, 1):
            lines.append(
                f"  {i}. angle={entry.angle}, form={entry.literary_form}, "
                f"narrator={entry.narrator}, opened with: \"{entry.first_three_words}\""
            )
        lines.append("")

    lines.append(
        "Write the caption now. Return only the caption text — nothing else."
    )

    return "\n".join(lines)


def roll_parameters(rng: Optional[random.Random] = None) -> dict:
    """Draw one random value from each rotation dimension."""
    r = rng or random
    return {
        "literary_form": r.choice(LITERARY_FORMS),
        "narrator": r.choice(NARRATORS),
        "tone": r.choice(TONES),
        "sensory_device": r.choice(SENSORY_DEVICES),
        "seed_noun": r.choice(SEED_NOUNS),
    }


# ─── Period-voice fallback templates ───────────────────────────────────
#
# When Gemini fails twice in a row, we still do not abandon the voice. These
# hand-written templates are plain period-style substitutes — safer than an
# AI output, still consistent with the brand.

_PERIOD_FALLBACK_TEMPLATES = {
    "clear": [
        "The sky at {city} stands clear, the air at {temp} degrees.",
        "{city} at {temp} degrees; no cloud is to be observed.",
        "A clear hour at {city}, {temp} degrees; nothing more is to be reported.",
    ],
    "clouds": [
        "{city} at {temp} degrees; the sky, low and considering.",
        "A covered sky over {city} at {temp} degrees — plain weather, and little to add.",
        "{city}: {temp} degrees, the clouds in full possession.",
    ],
    "rain": [
        "{city}: {temp} degrees, with a rain that has not yet decided its hour.",
        "A rain upon {city}, {temp} degrees; the streets take it quietly.",
        "{city} at {temp} degrees, rain falling without ceremony.",
    ],
    "drizzle": [
        "A small rain upon {city}, {temp} degrees; the kind that barely stirs the dust.",
        "{city} at {temp} degrees, and a drizzle not worth complaint.",
    ],
    "thunderstorm": [
        "{city}: {temp} degrees, with the weather lately turned hostile.",
        "Thunder at {city}, {temp} degrees; an afternoon of the usual theatre.",
        "A storm upon {city} at {temp} degrees; the sky in loud disagreement.",
    ],
    "snow": [
        "Snow upon {city}, {temp} degrees; the town half-hidden and patient.",
        "{city} at {temp} degrees, with snow enough to soften the stones.",
        "Snow at {city}, {temp} degrees; the kind of cold that keeps its word.",
    ],
    "fog": [
        "A fog over {city}, {temp} degrees, and the view curtailed.",
        "{city} at {temp} degrees, the fog keeping its own counsel.",
    ],
    "mist": [
        "A mist lies over {city} at {temp} degrees; the air dim and slow.",
        "{city}: {temp} degrees, under a mist of no great ambition.",
    ],
    "haze": [
        "{city} at {temp} degrees, the haze thin but general.",
        "A haze upon {city}, {temp} degrees; the light softened rather than spoiled.",
    ],
}

_DEFAULT_FALLBACK_TEMPLATES = [
    "The weather at {city}: {temp} degrees, and {condition} to report.",
    "{city} at {temp} degrees — plain weather, and {condition}.",
]


def build_period_fallback(
    city_name: str,
    temperature_c: float,
    main_condition: str,
    description: str,
    rng: Optional[random.Random] = None,
) -> str:
    """Produce a period-voice fallback caption when Gemini cannot be trusted.

    Picks one of several hand-written templates keyed on `main_condition`,
    or a generic period-voice fallback if the condition is not mapped.
    """
    r = rng or random
    key = (main_condition or "").lower()
    templates = _PERIOD_FALLBACK_TEMPLATES.get(key)
    temp_int = round(temperature_c)

    if templates:
        return r.choice(templates).format(city=city_name, temp=temp_int)

    return r.choice(_DEFAULT_FALLBACK_TEMPLATES).format(
        city=city_name,
        temp=temp_int,
        condition=description or "nothing singular",
    )
