# Digital Marketing

## Marketing funnel (stage -> goal -> metric)
- **Awareness** -> reach new audiences -> impressions, reach, CPM, brand search volume.
- **Consideration** -> earn engagement/intent -> CTR, sessions, time-on-page, email signups, lead volume.
- **Conversion** -> turn intent into purchase -> conversion rate (CVR), CAC, ROAS.
- **Retention** -> repeat + expand -> repeat rate, churn, LTV, NPS, email re-engagement.
- Funnel is leaky: 100 aware -> 10 consider -> 1 convert is normal; fix the biggest-drop stage, not the smallest.
- Full-funnel budget rule of thumb: don't pour 100% into bottom-funnel (retargeting/branded search) — it harvests demand you must also create up top.

## Core metrics + formulas
- **CAC** = total sales+marketing spend / new customers acquired.
- **LTV** (simple) = ARPU x gross margin % x average customer lifespan (or ARPU x GM% / churn rate).
- **LTV:CAC** — target ≥ 3:1; < 1 loses money per customer; > 5 may mean under-investing in growth.
- **CAC payback** = CAC / (monthly gross profit per customer); target < 12 months for SaaS.
- **ROAS** = revenue from ads / ad spend. Breakeven ROAS = 1 / gross margin %. (40% margin -> breakeven ROAS 2.5x.)
- **CTR** = clicks / impressions. **CVR** = conversions / clicks (or / sessions).
- **CPM** = cost per 1,000 impressions; **CPC** = cost per click = CPM / (CTR x 10); **CPA/CPL** = cost per acquisition/lead.
- **AOV** = revenue / orders. Revenue = traffic x CVR x AOV — three levers to grow.

## Channels
- **SEO** — organic search; compounding, slow (3-9mo), high trust, no per-click cost.
- **SEM / PPC** (Google/Bing Ads) — paid search; instant, intent-rich, auction-priced, stops when budget stops.
- **Paid social** (Meta, TikTok, LinkedIn) — interest/behavior targeting; great for demand *creation* + retargeting.
- **Email** — owned channel, highest ROI, best for retention/nurture; requires a list.
- **Content** (blog, video, guides) — fuels SEO + top-funnel; measure assisted conversions not last-click.
- **Affiliate / influencer** — pay-for-performance or sponsored; watch for fraud + brand fit.
- Owned (site, email, SMS) > earned (PR, word of mouth) > paid (ads) for margin; paid buys speed, owned buys durability.

## SEO basics
- **On-page**: title tag (~50-60 chars, keyword front), meta description (CTR, not ranking), H1/H2 structure, keyword in first 100 words, internal links, descriptive URLs, image alt text, search intent match (informational/navigational/transactional).
- **Technical**: crawlability (robots.txt, XML sitemap), indexation, site speed / Core Web Vitals (LCP, INP, CLS), mobile-friendly, HTTPS, canonical tags (dedupe), structured data (schema.org), no broken links/redirect chains.
- **Off-page**: backlinks (authority + relevance > volume), digital PR, unlinked brand mentions; avoid paid/spammy link schemes (penalty risk).
- Target long-tail keywords early (lower difficulty, higher intent); match content to intent, not just keyword.

## Paid ads mechanics
- **Targeting**: demographics, interests, behaviors, custom audiences (uploaded lists), lookalikes/similar audiences, retargeting (site/engagement), keyword + geo + device.
- **Bidding**: manual CPC, target CPA, target ROAS, maximize conversions; smart bidding needs ~30-50 conversions/mo to learn.
- **Quality Score** (Google, 1-10) = expected CTR + ad relevance + landing-page experience. Higher QS -> lower CPC + better position. Improve via tight ad-group-to-keyword-to-landing-page match.
- **Ad structure**: campaign (budget/goal) > ad group (theme) > ads + keywords. Tight themes beat one giant ad group.
- Creative + offer drive most of paid-social performance; test hooks/thumbnails first, then audiences.

## Attribution models
- **Last-click**: 100% credit to final touch — overcredits bottom-funnel/branded search.
- **First-click**: 100% to first touch — overcredits awareness.
- **Linear**: equal credit across touches.
- **Time-decay**: more credit closer to conversion.
- **Position-based (U-shaped)**: 40/20/40 first/middle/last.
- **Data-driven**: algorithmic credit from conversion-path data (needs volume).
- No model is "true"; use as directional. Triangulate with incrementality tests (geo holdouts, ghost ads) and marketing-mix modeling for privacy-safe measurement.

## A/B testing landing pages
- Test one primary variable (headline, CTA, hero, form length, social proof) or use multivariate only with high traffic.
- Compute sample size before launch (baseline CVR, minimum detectable effect, power 80%, α 0.05); run ≥ 1-2 full business cycles.
- Reach statistical significance (p < 0.05) AND practical significance; don't peek/stop early (inflates false positives).
- One conversion event = one goal per test; avoid confounds (don't change traffic source mid-test).

```
Sample-size intuition: smaller expected lift -> exponentially more traffic.
Detecting 2% -> 2.2% lift needs far more visitors than 2% -> 3%.
```

## Email
- **Segmentation**: by lifecycle stage, behavior, purchase history, engagement recency; segmented/triggered emails beat batch-and-blast.
- **Deliverability**: authenticate with SPF, DKIM, DMARC; warm up new domains/IPs; keep complaint rate < 0.1% and bounce < 2%; sunset unengaged subscribers; avoid spam-trigger tactics + purchased lists.
- **KPIs**: open rate (unreliable post-Apple MPP), click rate, CTOR (clicks/opens), conversion, unsubscribe, list growth, revenue per email.
- Lifecycle flows: welcome, abandoned cart, post-purchase, win-back, re-engagement.

## Analytics (GA4 concepts)
- Event-based model (every interaction = an event) — no more sessions-first like Universal Analytics.
- Key objects: events, parameters, conversions (key events), audiences, user vs session scope.
- Track funnels with exploration reports; set up UTM parameters (source/medium/campaign) consistently for channel attribution.
- Watch for: bot traffic, self-referrals, unfiltered internal traffic, sampling on large date ranges.

## Pitfalls -> Fix
- **Optimizing vanity metrics** (impressions, followers, likes) -> tie every channel to a revenue or pipeline KPI; report CAC/ROAS/LTV.
- **Ignoring LTV:CAC** -> price acquisition against lifetime value, not first-order revenue; cut channels below 3:1.
- **No attribution / last-click only** -> add position-based or data-driven view; run incrementality/geo holdout tests.
- **Judging channels on last-click** -> credit assisted conversions; content/top-funnel look "unprofitable" under last-click.
- **Stopping A/B tests early on a "win"** -> pre-commit sample size + duration; wait for significance across full cycles.
- **Scaling before product-market fit** -> paid ads amplify a leaky funnel; fix CVR + retention first.
- **Sending to a cold/purchased list** -> tanks deliverability + sender reputation; grow opt-in list, authenticate domain.
- **Keyword stuffing / thin content for SEO** -> write for intent + depth; one strong page beats ten thin ones.
- **Same creative forever (ad fatigue)** -> rotate creative; watch frequency + declining CTR; refresh hooks.
- **Retargeting everyone forever** -> cap frequency, exclude converters, set membership durations.
- **No conversion tracking / broken UTMs** -> validate pixels/tags and UTM taxonomy before spending; garbage in = garbage attribution.
- **Discounting to drive CVR** -> trains customers to wait for sales, erodes margin + brand; test value messaging first.
- **Chasing every new channel** -> concentrate on 2-3 channels that fit your buyer + margin before diversifying.

## Positioning + messaging
- Nail **who** (target segment), **what** (offer/category), and **why you** (differentiated value) before scaling spend.
- **Value proposition** = outcome delivered + for whom + why better than alternatives; test it in ad copy + landing hero.
- **Message-market fit** precedes channel scaling: if cold traffic doesn't convert, the offer/message is the problem, not the ad account.
- Match copy to funnel stage: education/pain up top, proof + differentiation mid, urgency + risk-reversal (guarantee, trial) at conversion.

## Budgeting + testing cadence
- Split budget across **test** (small, exploratory) and **scale** (proven winners); reserve ~10-20% for continuous experimentation.
- Kill losers fast on leading indicators (CTR, CPC, hook rate); scale winners gradually (20-30% steps) so learning phases don't reset.
- Track blended CAC (all spend / all new customers) alongside per-channel CAC to catch attribution over-crediting.
- Reallocate to marginal ROAS, not average: spend to the point where the next dollar still clears breakeven ROAS.

Consult platform docs + a specialist for regulated verticals (finance, health, political ads have ad-policy + privacy constraints).
