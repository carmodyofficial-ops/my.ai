# Writing & Communication

## Know the audience
- Name the one reader: exec, engineer, end user, future-you? Match depth, jargon, and what you justify to them.
- State what they already know and skip it; fill only the gap they need to act. Don't explain the obvious; don't assume the surprising.
- Know the reader's *job*: what decision or action does this doc enable? Write to that, cut the rest.
- Register/tone: match formality to channel and stakes. Neutral-direct by default; warmer for feedback, tighter for incidents. Never sarcastic in writing — tone doesn't survive the wire.

## Lead with the point (BLUF)
- First sentence = the answer/ask/outcome. Then justify. Readers skim; reward line 1.
- Bad: "After investigation, we found…" Good: "Login fails on Safari; cause: cookie SameSite=None without Secure."
- Put the ask in the subject/first line of any message: "Need approval by Fri to ship X."
- Inverted pyramid: conclusion → key support → detail → background. A reader can stop at any point and still have the gist.

## Structure
- One idea per paragraph; one idea per sentence. Headers so the doc is scannable, not readable-only.
- Chunk: group related points under labeled sections; 3-7 items per group. Lists for parallel items, prose for flowing logic/causation.
- Parallelism: keep list items the same grammatical shape ("Adds X / Fixes Y / Removes Z"). Mismatched forms read as sloppy thinking.
- Signposting: "Three risks:", "First… Second…", topic sentence leads each section. Short sentences; break any clause over ~25 words.

## Clarity
- Active voice: "X parses Y" not "Y is parsed by X". Name the actor — passive hides who does what.
- Strong verbs over noun phrases: "decide" not "make a decision"; "fails" not "is experiencing a failure".
- Cut filler: "in order to"→"to", "due to the fact that"→"because", delete "actually / basically / just / very / really".
- Concrete over abstract: "cut load time 2s→400ms" not "improved performance." Numbers and nouns, not adjectives.
- One meaning per term: pick a word for a concept and reuse it; don't elegant-variation ("user"/"customer"/"account" for the same thing).

## Formatting for the eye
- Front-load the sentence: put the subject and verb early; bury qualifiers and caveats at the end, not before the point.
- Use tables for anything with 2+ dimensions (option × criteria); use numbered lists for sequences/steps, bullets for unordered sets.
- Bold the load-bearing phrase per paragraph so a skimmer catches the spine. Don't bold more than ~10% — over-emphasis emphasizes nothing.
- Code, commands, filenames in monospace; never paraphrase an exact string the reader must copy.
- Whitespace is structure: a blank line between ideas beats a longer paragraph.

## Persuasion (claim → evidence → reasoning)
- State the claim, give the evidence (data, example, citation), then the reasoning that links them. Missing the link is the most common gap.
- Address the strongest counterargument explicitly; conceding it builds trust more than ignoring it.
- Lead with the reader's interest, not yours: frame the ask as their benefit or their risk avoided.

## Documents by type
- **PR description**: what changed / why / how to test / risk & rollback. Each a few lines. Reviewer should never have to guess intent.
- **Commit**: imperative subject ≤50 chars ("Add retry to upload"); blank line; body = *why* + tradeoff, not what (diff shows what).
- **Email/async**: subject states outcome + action; BLUF first line; bold the ask and deadline; keep to one screen.
- **RFC/design doc**: problem & goals / non-goals / options considered / decision + rationale / risks / rollout. Non-goals prevent scope fights.
- **Incident writeup**: impact (who/how long/how much) → timeline → root cause → remediation → prevention. Blameless: systems and gaps, not people.
- **README**: what it is, why it exists, how to run, one runnable example — in that order.

## Editing (multi-pass)
- Separate drafting from editing; don't polish a sentence you may cut. Pass 1 structure (does order/argument hold?), pass 2 clarity (sentences, active voice), pass 3 concision (cut 10-20%), pass 4 proofread (typos, names, numbers, links).
- Read aloud — you hear run-ons and clunk the eye skips. Cut the first paragraph; it's usually throat-clearing warmup.
- Delete every word that doesn't change meaning. If a sentence can go, it goes.

## Plain language
- Prefer the short common word: "use" not "utilize", "help" not "facilitate", "about" not "approximately".
- Define jargon once at first use, then reuse the term. Expand every acronym on first appearance.
- Write to be understood on first read by the least-context reader in the audience.

## Meetings & async
- Async default: write the decision + context so no meeting is needed. If you meet, send an agenda before and a decision/owner/next-step summary after.
- Make asks explicit and assign an owner + date; "someone should" gets done by no one.

## Feedback
- Specific + actionable + kind. SBI: Situation, Behavior, Impact ("In the review (S), the API lacked examples (B), so I couldn't integrate (I)"). Critique the work, not the person.
- Lead with what to change and how; praise the fix path, not just the flaw.
- Separate blocking from non-blocking: label "must fix" vs "nit/optional" so the reader triages. Unlabeled feedback all reads as mandatory.
- Ask, don't command, when intent is unclear: "what happens if input is empty here?" surfaces the issue without presuming a mistake.
- Receiving: assume good intent, extract the signal, thank; argue the substance, not the tone.

## Storytelling with structure
- Situation → Complication → Resolution (SCR), or Problem → Solution → Result. Tension then release keeps attention.
- One narrative spine, one takeaway per doc. Concrete example first, then the general rule; analogy to bridge the unfamiliar.
- Show, don't assert: a specific before/after ("was 8 clicks, now 2") persuades more than "much simpler."
- Pyramid principle: one governing thesis, supported by 3-4 grouped arguments, each backed by evidence. Reader gets the point at the top, drills only where they doubt.

## Explaining hard things
- Concrete example first, then the general rule; the abstraction lands only after a case to hang it on.
- Build from the reader's existing model: bridge from what they know to what they don't ("it's like a queue, but…").
- Progressive disclosure: give the working mental model first, then the caveats and edge cases; don't front-load exceptions.
- Name the thing once and consistently; a stable vocabulary is half of clarity.

## Titles, subjects, openers
- Title states the content, not the category: "Q3 retention dropped 4pts — cause and fix" beats "Retention Update."
- Email subject = outcome + action + deadline: "Approve budget by Thu (blocks launch)."
- Opening line earns the read: state the news or the ask, never "I hope this finds you well" as line one of substance.
- End with the next step: what you want the reader to do, by when, and how they respond.

## Global vs local edits
- Fix structure before sentences: no point polishing a paragraph you'll delete. Outline-level problems dominate word-level ones.
- Cut whole sections that don't serve the reader's decision, however well-written — kill your darlings.
- Consistency pass: one term per concept, one tense, one voice, one heading style, one number format throughout.

## Pitfalls -> Fix
- Burying the lede -> move the conclusion/ask to line 1.
- Wall of text -> add headers, lists, whitespace; chunk into labeled sections.
- Jargon/acronym soup -> define once, prefer the plain word, expand acronyms.
- Passive/vague ("this", "it", "was done") -> name the actor and the noun.
- Hedging ("should / might / maybe") -> state it or test it; give a number.
- No structure -> impose inverted pyramid or SCR before writing prose.
- Writing for yourself -> reread as the target reader; cut what they already know, add what they need to act.
- Weak verbs + nominalizations -> replace "make a decision" with "decide".
- No ask -> end with owner, action, and deadline.
