## Context

Today each social platform's caption is built by a small Python function that interpolates weather fields into fixed line templates. The three functions (`twitter.py:build_tweet_text`, `instagram.py:build_caption`, `tiktok.py:build_description`) each produce a slightly different readout of the same data, and the result reads as dashboard output — accurate but lifeless. Meanwhile the images themselves are AI-generated literary miniatures (isometric city dioramas). There is a mismatch between image quality and caption quality.

The app posts every 5 hours (~150 posts/month) to 3 platforms per post. Each post currently produces identical captions regardless of what's happening in the weather — there is no "editorial judgment" about which facts are interesting. Humidity of 77% is always surfaced as "💧 Humidity: 77%" whether that's notable or not.

We've decided to replace the template builders with AI-generated literary captions. The design below covers **how** that pipeline works end-to-end.

## Goals / Non-Goals

**Goals:**
- Produce captions that read like short literary weather vignettes, distinct per post even under identical weather conditions.
- Separate **what to say** (notability scoring — which weather signal is worth a post) from **how to say it** (Gemini prose generation with literary style constraints).
- Keep total incremental cost under $5/month.
- Never fail a post because of caption generation: every failure path lands on a clean minimal template.
- Make every piece independently testable: notability scoring is a pure function; prompt assembly is a pure function; only the Gemini call itself is I/O.
- Surface interesting facts; suppress mundane ones.

**Non-Goals:**
- Generating the images themselves (unchanged — still Nano Banana).
- Producing different-language captions (English only; Hebrew / other languages are a future change).
- Real-time weather alerts or emergencies (this is an aesthetic bot, not a safety channel).
- Adapting per-user tone / personalization; all readers see the same caption.
- Perfect consistency: we embrace variance as a feature, not a bug.

## Decisions

### D1: Gemini 2.5 Pro over Gemini 3 Pro Preview or Flash

**Choice:** Use `gemini-2.5-pro` as the default model.

**Why not 3 Pro Preview:** 3 Pro is ~60% more expensive on input and is labeled "Preview" — API and pricing can change. For a bot that must post reliably every 5 hours, we want GA stability.

**Why not Flash:** Flash is ~10x cheaper but noticeably more cliché-prone on literary prose. We're paying for quality here.

**Cost implication:** ~$3.50/month (3 calls × 150 posts × ~4.7k input + ~200 output tokens at $1.25/M input, $10/M output).

**Revisit trigger:** if 3 Pro graduates to GA and side-by-side evaluation on 20 real posts shows noticeably better outputs, flip the model in config.

### D2: Three Gemini calls per post (one per platform), not one shared call

**Choice:** Call Gemini once per enabled platform.

**Rationale:**
- Each platform has a different length target (Twitter 260 chars, Instagram 300-800, TikTok 80-180). Asking one call to produce three outputs of different sizes is error-prone.
- Each platform has a different voice target (Twitter terse, Instagram reflective, TikTok hook-forward). Specializing the prompt per platform produces better output.
- Extra cost is marginal (~$1/month total), not a constraint.

**Alternative considered:** One call that produces a single long body + we trim/expand per platform. Rejected: trimming breaks sentence integrity; Gemini is much better at writing to a length than we are at cutting to one.

### D3: Separate notability scoring from prose generation

**Choice:** A pure-Python notability scorer picks the "angle" before Gemini is ever called. Gemini receives the already-chosen angle as a constraint.

**Rationale:**
- Deterministic, testable, debuggable. We can unit-test which angle a given weather state produces.
- Keeps Gemini focused on the "writing" job, not the "editorial" job. LLMs are unreliable at "what's most newsworthy" when given a full data dump.
- Lets us tune editorial policy (what we find notable) without touching the generation prompt.
- Lets us steer away from recently-used angles with a clean integration point.

**Alternative considered:** Let Gemini see the full weather data and pick its own angle. Rejected: produces repetitive output (always picks the most obvious fact), harder to prevent repetition across posts, no introspection when a bad angle is chosen.

### D4: Variable-parameters rotation (the anti-sameness engine)

**Choice:** Every Gemini call receives a randomly-rolled tuple of stylistic parameters: `literary_form`, `narrator`, `tone`, `sensory_device`, and a `seed_noun` drawn from a 200+ item list.

**Rationale:**
- These parameters change what Gemini writes even when the weather is identical.
- `seed_noun` is the strongest differentiator: requiring the LLM to incorporate an arbitrary concrete image (e.g., "a brass bell", "an unread letter") forces compositional novelty.
- Combinatorial space: ~6 forms × 6 narrators × 7 tones × 6 devices × 200 seeds = ~300k combinations. Effectively unlimited for 150 posts/month.

**Alternative considered:** Pure temperature-based randomness (just set temperature=1.0). Rejected: produces random word choice but same structure; temperature alone doesn't change *what the post is about*.

### D5: Per-city anti-repetition memory (last 10 posts)

**Choice:** Maintain `state/caption_history.json` keyed by city, storing the last 10 captions' metadata (timestamp, primary_angle, literary_form, narrator, tone, first 3 words).

**Rationale:**
- Passed into each prompt as context; Gemini is instructed to avoid reusing these angles / forms / opening words.
- Also feeds into the notability scorer to deprioritize recently-used angles.
- 10 entries ≈ 2+ days of history at 5-hour cadence — enough to notice patterns, not enough to starve the system.

**Storage:** JSON file colocated with existing recently-posted state.

**Alternative considered:** No memory, rely on seed_noun alone. Rejected: even with seed_noun rotation, a human reader looking at a city's last 5 posts would see if we always lean on the same "angle". Memory fixes that.

### D6: Forecast via OpenWeatherMap /forecast (free tier), not OneCall 3.0

**Choice:** Use the free 5-day / 3-hour forecast endpoint. Pull 8 entries (24h of forecast) per post.

**Rationale:**
- Already have the API key, same base URL pattern.
- Free tier is generous (60 calls/min) — we use ~5 calls/day.
- 3-hour resolution is sufficient for "rain in 3 hours" / "clearing by 6pm" kinds of statements.

**Alternative considered:** OneCall API 3.0 (1000 free calls/day). Richer data but adds a second API pattern for no real gain at our volume.

### D7: System-prompt structure — heavy on constraints and examples

**Choice:** System prompt is split into fixed sections:
1. Role statement (literary weather correspondent)
2. Hard constraints (length per platform, no hashtags on Twitter, must include temp + condition)
3. Style guide (elevated register, sensory detail, one strong image beats three weak ones)
4. Forbidden-cliché list (10+ banned phrases with explanation)
5. Four to six few-shot examples with short "why this works" annotations
6. Output format (raw caption text only, no explanations, no markdown)

**Rationale:**
- Few-shot examples are the single biggest quality lever for literary output.
- Forbidden-cliché list is needed because default LLM output drifts toward these phrases.
- "Why this works" annotations in examples act as implicit style rules.
- Hard constraints before style to prevent valid-but-wrong output (too long, contains banned words).

### D8: Validation as sensor, not gate — no retries

**Choice:** Make exactly one Gemini call per caption. Validation runs on the output, but stylistic slips (cliché, missing temp, missing condition) are *recorded* in a JSONL glitch log, not blocked. The caption is posted unchanged. Only hard failures (empty response, exception, timeout) trigger the period-voice fallback.

**Rationale:**
- Retries cannot actually fix deep style problems. A correction hint patches the symptom, not the cause. Real improvement comes from iterating on the system prompt, examples, and cliché list.
- The glitch log *is* the learning signal. After two months of data, you see which rotation params produce clichés, which angles drift, which seed nouns lead Gemini astray — and tune the prompt accordingly.
- One slip per hundred posts is acceptable; a worse-but-consistent voice is better than a clean-but-off-brand one.
- Removes ~60 lines of retry/correction-hint code (`_build_correction_hint`, retry loop, `correction_hint` plumbing through `build_user_prompt`). Simpler.
- Halves worst-case cost and latency per post (one Gemini call vs. two).

**What stayed:** The `_diagnose` method (was `_validate`) still runs the three checks — cliché scan, temperature reference, condition reference — but the output feeds the glitch log, not a retry decision.

**What was dropped:** Length validation entirely. Posting accounts are verified and accept long posts; trimming Gemini's output would damage the voice for no gain.

**Alternative considered:** Keep retries for length-only failures, drop retries for style. Rejected: length isn't actually a concern (verified account), so the code path becomes dead.

**Alternative considered:** One-shot generation, no validation at all. Rejected: we lose the learning signal and can't catch drift without it.

### D9: Hashtags stay template-driven

**Choice:** Gemini generates the caption body only. Instagram and TikTok hashtag blocks are still generated by existing template code and appended after the AI body. Twitter gets no hashtags (already removed).

**Rationale:**
- Hashtags are mechanical, not literary. No reason to pay Gemini to produce them.
- Keeping existing hashtag logic reduces blast radius of this change.
- Simpler validation (LLM can't accidentally strip hashtags).

### D10: Output format — raw text, no JSON wrapping

**Choice:** System prompt instructs Gemini to return caption text only, no JSON, no markdown, no explanations.

**Rationale:**
- Simplest possible contract. Fewer parsing failure modes.
- Downstream code treats Gemini output as opaque string, post-processes only for appending hashtags.

**Alternative considered:** JSON output with `{caption, chosen_angle, notes}`. Rejected: adds parsing complexity for no runtime value; introspection fields can live in logs.

## Risks / Trade-offs

**[Risk] Gemini drifts toward clichés over time or produces generic output** → Mitigation: forbidden-cliché validator catches the common cases and retries. Periodic manual review of outputs should feed new clichés into the ban list.

**[Risk] Caption occasionally exceeds Twitter's 280-char limit** → Mitigation: we target 260 as the hard cap (20-char safety margin); validator rejects over-length; retry with correction hint; template fallback ensures post still ships.

**[Risk] Gemini API outage stalls posting** → Mitigation: 30s timeout + template fallback. Posts always ship, possibly with lower-quality caption.

**[Risk] Caption omits the temperature or conditions (literary but factless)** → Mitigation: weather-fact validator rejects captions lacking temp + condition; retry; fallback.

**[Risk] Cost creep from retries or over-long outputs** → Mitigation: `max_output_tokens=400` hard cap + retry budget of 1. Worst-case monthly cost bounded at ~$7/month even if every call retries once.

**[Risk] Notability scorer picks a bad angle (e.g., "perfect_day" for a rain-and-freeze scenario)** → Mitigation: rule set is explicit and deterministic; misclassifications produce reproducible bug reports. Unit tests cover major weather states.

**[Risk] Anti-repetition memory starves interesting angles** (e.g., all-rain week blocks "rain_now_clearing" from ever being picked) → Mitigation: penalty is -3/-5, not elimination. If the signal is otherwise-dominant, it still surfaces.

**[Risk] Forecast endpoint failure silently changes behavior** → Mitigation: empty forecast gracefully handled by scorer; derived fields return safe defaults; log the failure.

**[Risk] Few-shot examples bias outputs toward the examples' subject matter** → Mitigation: examples deliberately span varied conditions (sun, rain, fog, cold, hot) and varied cities.

**[Risk] Per-city `character` hint produces stereotyped output** → Mitigation: `character` is an optional, neutral-tone hint ("small Caribbean island", "alpine town") — not a cultural caricature. Default empty.

## Migration Plan

**Phase 1 — build offline (no posting impact):**
- Implement `src/notability.py` + unit tests covering all 20 signal categories.
- Implement `src/weather.py` forecast extension + unit tests for empty/partial responses.
- Implement `src/caption_memory.py` + unit tests for rotation.
- Write the system prompt in `src/caption_prompts.py` with 6+ few-shot examples.

**Phase 2 — dry-run validation:**
- Implement `src/caption_generator.py` end-to-end.
- Run with `--dry-run` on 20 cities across varied weather conditions; manually review generated captions.
- Tune: forbidden-cliché list, few-shot examples, validator thresholds.
- Iterate until subjective quality bar is met.

**Phase 3 — live rollout:**
- Wire up platform posters (`twitter.py`, `instagram.py`, `tiktok.py`) to call caption generator.
- Keep template methods as `_build_fallback_*` for the fallback path.
- Ship.

**Rollback:** revert platform poster wiring only. Notability/forecast/memory modules can stay (they don't run unless called).

## Open Questions

- **Per-city character hints**: worth it now, or wait until we see default outputs? **Proposal**: ship without; add later if outputs feel too generic across cities.
- **Logging level of Gemini responses**: do we log full prompts + responses for debugging? **Proposal**: yes, at `DEBUG` level, with a separate log file to keep main log clean.
- **How to seed the `seed_noun` list**: hand-curated 200 nouns, or mix in generated ones? **Proposal**: hand-curated initial list, revisit if outputs feel narrow.
