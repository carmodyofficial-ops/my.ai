# Investigation & Research Methods

## 1. Frame the question
- State precisely what you're answering and why. Ask: *what decision does this change?* If no answer alters an action, stop.
- Scope it: version, platform, timeframe, constraints, success threshold. Bad: "is X fast?" Good: "is X's p99 < 50ms for 10k writes/s on v2.3?"
- Surface assumptions and unknowns up front; split a fuzzy question into answerable sub-questions. Define terms so you don't conflate two things.

## 2. Source strategy: primary > secondary
- **Primary** (direct evidence): source code, official docs, specs/RFCs, changelogs, datasets, original studies, first-hand accounts.
- **Secondary** (interpretation): blogs, articles, textbooks, reviews, forum answers. **Tertiary**: encyclopedias, AI summaries, listicles — pointers, not proof.
- Ranking: source/spec > official docs > peer-reviewed/primary data > reputable secondary > forums > AI/SEO summaries. Trace every claim to the most primary source you can reach; open and read it — don't trust the snippet.

## 3. Evaluate sources & credibility
- Weigh **authority** (who wrote it; do they own/operate the system; credentials), **recency**, **bias/incentive** (vendor selling, ideology, funding), **corroboration**, **methodology** (sample size, controls, is it reproducible?).
- Primary-source proximity: eyewitness/maintainer > reporter > aggregator. Check the source's own citations — does the claim survive to a real origin, or circular-cite back to itself?
- Separate **fact** (verifiable), **opinion** (judgment), **speculation** (guess), **anecdote** (n=1). Label which you're relaying.

## 4. Systematic search
- Use specific terms, not vague ones. Paste error strings verbatim in quotes. Use `site:` (`site:docs.python.org`), version numbers, date filters, and GitHub code/issue search.
- Search iteratively: broad -> skim -> refine vocabulary from what experts call it -> targeted. Seek the opposing term too (`X vs Y`, `X problems`, `X deprecated`) to escape one framing.
- Keep a search log (queries tried, what each yielded) so you don't loop, and coverage is auditable.

## 5. Triangulate
- Require **>=2 independent** sources for any non-trivial claim — independent meaning not re-citing the same origin. Convergence from different methods/authors raises confidence; a chorus quoting one blog does not.
- When sources disagree, don't average — find *why*: different versions, definitions, conditions, or one is simply wrong. Resolve to the more primary/authoritative/recent.

## 6. Note-taking & synthesis
- Capture claim + source + date + confidence as you go (not from memory later); quote exact wording for load-bearing facts. Distinguish your paraphrase from a direct quote.
- Synthesize, don't summarize serially: group by theme, state the **consensus AND the disagreements** explicitly, attach confidence (high/med/low) and the reason. "Per <src A>, X; but <src B> contradicts on Y because <version>."
- Cite every claim with a link/path so it's checkable. If you can't cite it, say so and mark it an assumption.

## 7. Bias awareness
- **Confirmation bias**: actively seek disconfirming evidence; try to falsify your hypothesis, not confirm it. Ask "what would change my mind?"
- Watch cherry-picking, availability bias (first/loudest result), authority bias, recency vs stability, and motivated reasoning. Pre-register what a "yes" vs "no" looks like before you look.

## 8. Freshness / recency
- For fast-moving tech, recent > stale — always check publish/updated dates; a 2019 answer may be wrong for today's version. Confirm the source matches your version/platform.
- For settled fundamentals, age is fine. Prefer the current official doc + a changelog check over old highly-ranked blog posts.

## 9. Evaluate claims & evidence
- Grade evidence strength: replicated study/spec > single study/official statement > expert opinion > anecdote > rumor. Correlation isn't causation; watch confounders, small samples, and absolute-vs-relative numbers.
- Extraordinary claims need stronger evidence. Distinguish "no evidence for" from "evidence against". Note effect size and conditions, not just direction.

## 10. Reproducibility & debugging-as-research
- Reproduce first — never theorize before you've seen it fail. Isolate one variable at a time. Form an explicit hypothesis ("if it's the cache, clearing it fixes it"), then test it; let evidence pick the cause, don't guess-and-patch.
- Record method + environment so another person (or you, later) can rerun and get the same result. A finding you can't reproduce is a lead, not a conclusion.

## 11. Know when to stop
- Stop when you have enough to decide/act and new searching only repeats known points (saturation). Avoid analysis paralysis; ship the answer with its confidence, assumptions, and open questions.

## 12. Citation & traceability
- Record enough to re-find: title, author/org, URL or file path, version, publish/accessed date, and the exact locator (page/line/section/commit). A bare domain isn't a citation.
- Quote load-bearing text verbatim; paraphrase elsewhere but keep the link. Prefer permalinks/commit-pinned URLs over "latest" for anything that changes.
- Attribute every non-obvious claim inline so a reader can audit it; group a bibliography for reuse. If a source is paywalled/private, note that rather than dropping the citation.

## 13. Handling AI/LLM outputs as sources
- Treat model output as an unverified lead, not a source — it fabricates plausible citations and facts. Verify each claim against a real primary source before relaying.
- Ask for and follow the underlying sources; if none survive to a real origin, discard the claim. Never cite "the model said so".

## Pitfalls -> Fix
- Cherry-picking evidence that fits -> pre-commit to criteria; report disconfirming findings too.
- Stale / SEO-spam sources -> check date + author; prefer current primary docs.
- Single-source claims -> corroborate with an independent source or flag as unverified.
- Confirmation bias -> actively hunt disconfirming evidence; state what would change your mind.
- No synthesis (a link dump) -> integrate into a claim with consensus, disagreement, and confidence.
- Accepting a summary without reading the primary -> open the source; verify the quote survives to origin.
- Theorizing before reproducing -> reproduce, isolate one variable, then hypothesize.
- Uncited assertions -> cite the path/link, or say it's an assumption.
- Mistaking correlation for causation / anecdote for data -> check method, sample, confounders, effect size.
