# Corpus Expansion + Dedup + Diversity

## Goal

Grow the Chroma corpus from 2,052 → ~6,000-8,000 posts with:
- **No duplicates** (exact text match + near-dup via embedding cosine sim)
- **No source domination** (cap N posts per URL/source so one Anthropic blog post doesn't contribute 50 chunks)
- **Quality filtering** (drop boilerplate: LinkedIn login walls, navigation chrome, "Source:" headers, etc.)
- **Voice purity** (prefer first-person posts BY the author over articles ABOUT them)

## Current state

- 2,052 docs in Chroma collection `ceo_posts`
- 11 authors, twitter (~20-58 each) + linkedin (~120-228 each)
- LinkedIn data is heavily contaminated with scraped news articles
- Many entries have visible scrape artifacts: `"Source: https://..."`, `"Agree & Join LinkedIn"`, etc.

## Audit script (run first to see what we have)

```python
# scripts/audit_corpus.py
# - exact dup count per author
# - boilerplate marker count (LinkedIn login walls, source headers)
# - source URL distribution per author (which URLs dominate)
# - first-person marker rate ("I ", "we ", "my ", "our ") per post
# - average post length, character distribution
```

## Cleanup pipeline

Process per author/platform JSON in `packages/api/data/profiles/`:

1. **Strip boilerplate** from each `example_posts` entry:
   - Remove lines starting with `Source:`, `Published:`, `# `, `## `
   - Remove "Agree & Join LinkedIn", "Sign in to LinkedIn", "Show me more content from"
   - Remove URLs from anywhere except quoted tweets
   - Collapse `\n{2,}` → `\n\n`, `[ \t]+` → ` `

2. **Filter out non-author content:**
   - If a post starts with `[Author Name] said` / `According to [Author]` / mentions the author in 3rd person consistently → flag as "about the author" not "by the author"
   - Drop "about" entries unless we have < 10 "by" entries for that author/platform

3. **Exact dedup:** dict keyed on normalized text (lowercase, whitespace-collapsed) → drop later collisions

4. **Near-dup detection:** embed all surviving posts per author. For each pair with cosine similarity > 0.92 → keep the longer one, drop the shorter.

5. **Source domination cap:** if a URL appears in > 10 entries (e.g., one earnings call transcript scraped 50 times) → keep top 10 most-distinct chunks.

## New scraping (additive)

After cleanup, for any author with < 100 quality posts, scrape more from these sources via Exa:

- **Personal blogs:** `blog.samaltman.com`, `tobi.lutke.com`, `paulgraham.com` (for collison/chesky quotes), `darioamodei.com`, etc.
- **Podcast transcripts:** "All-In Podcast", "Lex Fridman Podcast", "Acquired", "20VC" — these have rich first-person material
- **Conference talks:** YC startup school, Stripe Sessions, Anthropic conferences — search via Exa
- **Substacks/Newsletters:** authors that have one (Patrick Collison's footnotes, etc.)

For each scraped doc:
- Extract the section spoken/written by the author (skip interviewer questions)
- Chunk to 200-500 char passages (NOT full transcripts — diverse short snippets retrieve better)
- Tag `source_type` accurately: `blog`, `podcast`, `conference`, `interview`, `tweet`, `linkedin_post`

## Re-indexing

After cleanup + new scraping:
1. Wipe the Chroma collection (`store.delete_by_author(...)` for each author)
2. Re-run `scripts/index_posts.py`
3. Spot-check retrieval quality on 5 prompts from the demo set

## Anti-overfit measures (built into the retriever)

These are SMALL changes to `hybrid_retriever.py`:

- **Diversity bonus**: when querying Chroma for k=5, request k=10 then dedupe by cosine sim > 0.85 BEFORE returning. So you get 5 *diverse* matches, not 5 near-dups.
- **Source spread**: if all 5 hits come from the same source URL → reject and pull next-best from a different source.

## Files

```
scripts/
├── audit_corpus.py          # NEW: report current state
├── clean_profiles.py        # NEW: strip boilerplate, dedup, filter
├── scrape_blogs.py          # NEW: blog-specific scraper
└── index_posts.py           # EXISTING: extend with diversity-aware upsert

packages/api/src/writer_api/services/
└── hybrid_retriever.py      # EXTEND: diversity bonus + source spread on query
```

## Validation

After the run:
- `python scripts/audit_corpus.py` → total posts, per-author counts, dup count = 0
- Hit `/api/generate/moe` for 5 demo prompts → verify Chroma scores ≥ 0.25 on at least 3 of 5 own_posts (currently many are 0.05-0.10)
- Visual eyeball: are the retrieved posts actually about the topic, or random-author-spam?

## Out of scope

- Auth, rate limiting, frontend error states, judge bias fix → separate plan
- Re-extracting voice profiles (lexical/structural/tonal) → those were generated once at scrape time and have their own contamination. Could rebuild but that's a v2 problem.

## Subagent dispatch

This is a sequential pipeline (audit → clean → scrape → re-index). One subagent, not parallel. Should take 30-60 min depending on Exa quota.
