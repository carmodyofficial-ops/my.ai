# Technical Writing

## Audience + purpose (decide before writing)
- Name one primary reader; write to their role, goal, and prior knowledge — not to yourself.
- State the document's job in one line: teach a task, describe a system, explain a concept, or persuade a decision. Mixed jobs = confused doc.
- Answer up front: what will the reader be able to DO after reading? Cut anything not serving that.
- Match register to reader expertise: novice needs prerequisites + defined terms; expert needs signal, no hand-holding.
- Assume the reader is busy, skimming, and interrupt-driven. Optimize for scanning first, deep read second.

## Clarity principles (sentence level)
- Active voice, strong verbs: "Run `migrate`" not "the migration should be run." Names the actor.
- One idea per sentence. Split any sentence with two clauses joined by "and"/"which" doing real work.
- Concise: cut "in order to"→"to", "at this point in time"→"now", "utilize"→"use", "is able to"→"can".
- Parallelism in lists/headings: all start with a verb, or all noun phrases — never mixed.
- Prefer present tense, second person ("you"), imperative for instructions.
- Front-load the sentence: put the point first, conditions second. "Delete the file to reset" > "To reset, if you want, you can delete the file."
- Concrete over abstract: name the file, command, value. Avoid "the appropriate configuration."

## Structure (document level)
- Inverted pyramid: conclusion/answer first, supporting detail below, background last. Readers leave early.
- Chunking: one topic per section; 3–5 sentences or a short list per chunk. Break the wall of text.
- Scannability: descriptive headings (answer "what's in here"), bulleted lists, bold key terms, tables for comparisons, code blocks for code.
- Descriptive headings, not clever ones: "Configure TLS" > "Locking it down."
- Progressive disclosure: common path first; edge cases, advanced options, and troubleshooting after.
- One canonical location per fact (single source of truth); link, don't duplicate.

## Document types (Diataxis-aligned)
- Tutorial: learning-oriented; a guaranteed-success guided path for beginners; concrete, no choices, no theory.
- How-to guide: task-oriented; steps to achieve one goal for someone who already knows the basics; assumes context.
- Reference: information-oriented; dry, complete, consistent description (API params, flags, config keys); structured for lookup, not reading.
- Explanation: understanding-oriented; the why, background, trade-offs, alternatives; read away from the keyboard.
- Do not blend: a tutorial that stops to explain internals loses the beginner; reference prose that teaches loses the looker-upper.

## Writing for developers
- Every code sample must be copy-pasteable and actually run; test it.
- State prerequisites explicitly: versions, installed tools, credentials, OS assumptions.
- Show expected output/result after each command so readers can self-verify.
- Prefer minimal reproducible snippets over full-app dumps; highlight the changed lines.
- Explain non-obvious flags/args inline; never assume the reader knows the CLI.
- Give the copy-paste command AND what it does — not just one.

```
$ curl -s localhost:8080/health
{"status":"ok"}   # 200 means the server is up
```

## Style guides + terminology
- Adopt a style guide (Google, Microsoft, Chicago) to end bikeshedding on capitalization, hyphens, oxford comma.
- One term per concept, always: don't alternate "login/log in/sign in/authenticate" for the same action.
- Maintain a term glossary + a "do not use" list for the product.
- Define an acronym on first use: "single sign-on (SSO)"; then use the short form.
- Consistent formatting conventions: `code font` for literals, **bold** for UI labels, _italics_ for first-use terms.

## Editing passes (separate, in order)
1. Structure: is the order logical? does the answer come first? cut whole sections that don't serve the purpose.
2. Clarity: shorten sentences, kill passive voice, replace jargon, add missing steps.
3. Correctness: run every command, verify every claim, check versions/links.
4. Consistency: terms, capitalization, formatting, tense.
5. Proofread: typos, grammar — last, on fresh eyes or read aloud.
- Write drafty, edit ruthlessly. First draft ≠ shippable.

## Plain language + localization-friendly writing
- Short sentences (aim < 25 words), common words, no idioms/metaphors ("piece of cake", "kill two birds") — they mistranslate and exclude non-native readers.
- Avoid phrasal-verb ambiguity and culture-specific references.
- Use "you" and direct instructions; avoid nested negatives ("not uncommon").
- Keep UI strings and sentences translatable: avoid concatenating fragments; don't embed variables mid-idiom.
- Spell out, don't rely on left/right or color alone (accessibility + translation).

## Pitfalls -> Fix
- Assumes reader knowledge (curse of knowledge) -> List prerequisites; have a novice test the doc; define terms on first use.
- Wall of text -> Chunk into sections with headings, lists, and code blocks; one idea per paragraph.
- Undefined jargon/acronyms -> Glossary + expand-on-first-use; link to definitions.
- Passive, wordy sentences -> Active voice, cut filler, one idea per sentence.
- Burying the answer -> Inverted pyramid: put the conclusion/step first.
- Untested code samples -> Run every snippet in a clean environment before publishing.
- Missing expected output -> Show the result of each command so readers confirm success.
- Inconsistent terminology -> One term per concept; enforce with a style guide + glossary.
- Clever/vague headings -> Descriptive headings that state the section's content.
- Mixing doc types (tutorial + reference + explanation) -> Split by Diataxis; link between them.
- Duplicated facts drifting apart -> Single source of truth; link instead of copy.
- Instructions with gaps ("obviously, then deploy") -> Number every step; assume nothing between steps.
- Idioms/metaphors -> Plain literal language for translation + accessibility.
- Editing while drafting (writer's block) -> Draft first, edit in separate passes.
- "Click the button" with no location -> Name the exact label and where it is.
- Screenshots as the only source of truth -> Pair with text; screenshots go stale and aren't searchable/accessible.

## Formatting for comprehension
- Numbered lists for sequential steps; bulleted lists for unordered sets; never number things that aren't ordered.
- Tables for comparing options across attributes (feature vs. plan, flag vs. effect) — far scannable than prose.
- Notes/warnings/tips as callouts, sparingly: reserve "Warning" for data-loss/security; overuse trains readers to ignore them.
- Meaningful link text ("see the auth guide"), never "click here" — screen readers and scanners read links out of context.
- Code font for anything typed literally (commands, filenames, values, keys); prose font for concepts.
- Keep procedures to one action per numbered step; if a step has an "and", split it.

## Titles, intros, and orientation
- Title states the task or topic in the reader's words; front-load the keyword ("Configure OAuth", not "Getting things wired up").
- Opening sentence states what the doc covers and who it's for; skip "Welcome!" and throat-clearing.
- For how-tos, state the outcome and prerequisites before step 1.
- Provide an at-a-glance summary/TL;DR at the top of long docs.
- End with next steps / related links so readers aren't stranded.

## Numbers, units, and precision
- Be specific: "under 200ms", "up to 3 retries", "≥ Node 18" — not "fast", "several", "recent versions".
- State units and time zones; use ISO dates (2026-07-09) to avoid locale ambiguity.
- When stating limits/defaults, say the exact value and where to change it.

## Heuristics
- If a sentence survives deletion without loss, delete it.
- If you can't test a step, you can't ship it.
- Every "it depends" needs the deciding factor named.
- The reader skims; make headings a table of contents that answers their question.
- Write the title and first paragraph last, once you know what the doc actually says.
