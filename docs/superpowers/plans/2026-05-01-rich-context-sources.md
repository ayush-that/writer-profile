# Rich Context Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand profile context beyond social posts to include news articles, interviews, company info, and other relevant sources for richer, more informed post generation.

**Architecture:** 
- Add a context store alongside profiles to cache fetched content
- Extend ExaRetriever with methods for news, interviews, and company content
- Create a scraper script to populate context for all profiles
- Update generator to pull from multiple source types with source tagging
- Show source types in UI for transparency

**Tech Stack:** Exa API (search), FastAPI (backend), JSON file storage (context cache)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `packages/api/src/writer_api/services/context_store.py` | Store and retrieve cached context by author |
| `packages/api/src/writer_api/services/exa_retriever.py` | Add news, interviews, company search methods |
| `packages/api/src/writer_api/services/generator.py` | Fetch from multiple source types |
| `scripts/scrape_context.py` | Populate context cache for all authors |
| `data/context/{author}.json` | Cached context per author |

---

### Task 1: Create Context Store Service

**Files:**
- Create: `packages/api/src/writer_api/services/context_store.py`

- [ ] **Step 1: Create the context store service**

Create `packages/api/src/writer_api/services/context_store.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from writer_api.config import settings


@dataclass
class ContextItem:
    text: str
    url: str
    title: str
    source_type: str
    published_date: str | None = None


@dataclass
class AuthorContext:
    author: str
    updated_at: str
    news: list[ContextItem] = field(default_factory=list)
    interviews: list[ContextItem] = field(default_factory=list)
    company: list[ContextItem] = field(default_factory=list)
    podcasts: list[ContextItem] = field(default_factory=list)


class ContextStore:
    def __init__(self, context_path: str | None = None) -> None:
        self._path = Path(context_path or settings.profiles_path).parent / "context"
        self._path.mkdir(parents=True, exist_ok=True)

    def load(self, author: str) -> AuthorContext | None:
        filepath = self._path / f"{author}.json"
        if not filepath.exists():
            return None

        with open(filepath) as f:
            data = json.load(f)

        return AuthorContext(
            author=data["author"],
            updated_at=data.get("updated_at", ""),
            news=[ContextItem(**item) for item in data.get("news", [])],
            interviews=[ContextItem(**item) for item in data.get("interviews", [])],
            company=[ContextItem(**item) for item in data.get("company", [])],
            podcasts=[ContextItem(**item) for item in data.get("podcasts", [])],
        )

    def save(self, context: AuthorContext) -> None:
        filepath = self._path / f"{context.author}.json"

        data = {
            "author": context.author,
            "updated_at": context.updated_at or datetime.now().isoformat(),
            "news": [
                {
                    "text": item.text,
                    "url": item.url,
                    "title": item.title,
                    "source_type": item.source_type,
                    "published_date": item.published_date,
                }
                for item in context.news
            ],
            "interviews": [
                {
                    "text": item.text,
                    "url": item.url,
                    "title": item.title,
                    "source_type": item.source_type,
                    "published_date": item.published_date,
                }
                for item in context.interviews
            ],
            "company": [
                {
                    "text": item.text,
                    "url": item.url,
                    "title": item.title,
                    "source_type": item.source_type,
                    "published_date": item.published_date,
                }
                for item in context.company
            ],
            "podcasts": [
                {
                    "text": item.text,
                    "url": item.url,
                    "title": item.title,
                    "source_type": item.source_type,
                    "published_date": item.published_date,
                }
                for item in context.podcasts
            ],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def list_authors(self) -> list[str]:
        return [f.stem for f in self._path.glob("*.json")]
```

- [ ] **Step 2: Verify the module compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.context_store import ContextStore; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/services/context_store.py
git commit -m "feat(api): add context store service for rich author context"
```

---

### Task 2: Extend ExaRetriever with Rich Source Methods

**Files:**
- Modify: `packages/api/src/writer_api/services/exa_retriever.py`

- [ ] **Step 1: Add news, interview, and company search methods**

Replace the entire file with:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from exa_py import Exa

from writer_api.config import settings


@dataclass
class RetrievedContent:
    text: str
    url: str
    title: str
    source_type: str
    published_date: datetime | None


class ExaRetriever:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.exa_api_key.get_secret_value()
        self._client = Exa(api_key=key)

    def search_linkedin_posts(
        self,
        author_name: str,
        linkedin_handle: str,
        max_results: int = 20,
    ) -> list[RetrievedContent]:
        query = f"{linkedin_handle} {author_name}"
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            include_domains=["linkedin.com/posts", "linkedin.com/pulse"],
            text=True,
        )
        return self._to_retrieved_content(results.results, "linkedin")

    def search_news(
        self,
        author_name: str,
        max_results: int = 20,
    ) -> list[RetrievedContent]:
        query = f'"{author_name}" interview OR quote OR said OR announced'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            category="news",
            text=True,
        )
        return self._to_retrieved_content(results.results, "news")

    def search_interviews(
        self,
        author_name: str,
        max_results: int = 15,
    ) -> list[RetrievedContent]:
        query = f'"{author_name}" interview podcast conversation fireside chat'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            text=True,
        )
        return self._to_retrieved_content(results.results, "interview")

    def search_company_content(
        self,
        author_name: str,
        company_name: str,
        max_results: int = 15,
    ) -> list[RetrievedContent]:
        query = f'"{company_name}" {author_name} CEO announcement blog'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            text=True,
        )
        return self._to_retrieved_content(results.results, "company")

    def search_podcasts(
        self,
        author_name: str,
        max_results: int = 10,
    ) -> list[RetrievedContent]:
        query = f'"{author_name}" podcast episode transcript'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            include_domains=[
                "youtube.com",
                "spotify.com",
                "podcasts.apple.com",
                "transistor.fm",
            ],
            text=True,
        )
        return self._to_retrieved_content(results.results, "podcast")

    def search_for_generation(
        self,
        author_name: str,
        platform: str,
        topic: str,
        k: int = 5,
    ) -> list[RetrievedContent]:
        query = f'"{author_name}" {topic}'

        include_domains = None
        if platform == "linkedin":
            include_domains = ["linkedin.com"]
        elif platform == "twitter":
            include_domains = ["twitter.com", "x.com"]

        search_kwargs: dict = {
            "query": query,
            "type": "auto",
            "num_results": k,
            "text": True,
        }

        if include_domains:
            search_kwargs["include_domains"] = include_domains

        results = self._client.search_and_contents(**search_kwargs)
        return self._to_retrieved_content(results.results, f"{platform}_context")

    def search_topic_context(
        self,
        author_name: str,
        topic: str,
        max_results: int = 5,
    ) -> list[RetrievedContent]:
        """Search for what the author has said about a specific topic."""
        query = f'"{author_name}" {topic}'
        results = self._client.search_and_contents(
            query=query,
            type="auto",
            num_results=max_results,
            text=True,
        )
        return self._to_retrieved_content(results.results, "topic_context")

    def _to_retrieved_content(
        self, results: list, source_type: str
    ) -> list[RetrievedContent]:
        out: list[RetrievedContent] = []
        for r in results:
            text = r.text or r.title or ""
            if not text.strip():
                continue
            out.append(
                RetrievedContent(
                    text=text,
                    url=r.url or "",
                    title=r.title or "",
                    source_type=source_type,
                    published_date=self._parse_date(r.published_date),
                )
            )
        return out

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            return None
```

- [ ] **Step 2: Verify the module compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.exa_retriever import ExaRetriever; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/services/exa_retriever.py
git commit -m "feat(api): add news, interview, company, podcast search methods"
```

---

### Task 3: Create Context Scraper Script

**Files:**
- Create: `scripts/scrape_context.py`

- [ ] **Step 1: Create the context scraper script**

Create `scripts/scrape_context.py`:

```python
#!/usr/bin/env python3
"""Scrape rich context for all authors using Exa API."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the API package to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "api" / "src"))

from exa_py import Exa

EXA_API_KEY = os.environ.get("EXA_API_KEY")
CONTEXT_DIR = Path(__file__).parent.parent / "data" / "context"

AUTHORS = {
    "sam_altman": {"name": "Sam Altman", "company": "OpenAI"},
    "elon_musk": {"name": "Elon Musk", "company": "Tesla SpaceX X"},
    "brian_chesky": {"name": "Brian Chesky", "company": "Airbnb"},
    "guillermo_rauch": {"name": "Guillermo Rauch", "company": "Vercel"},
    "dario_amodei": {"name": "Dario Amodei", "company": "Anthropic"},
    "satya_nadella": {"name": "Satya Nadella", "company": "Microsoft"},
    "patrick_collison": {"name": "Patrick Collison", "company": "Stripe"},
    "tobi_lutke": {"name": "Tobi Lutke", "company": "Shopify"},
    "aravind_srinivas": {"name": "Aravind Srinivas", "company": "Perplexity"},
    "ali_ghodsi": {"name": "Ali Ghodsi", "company": "Databricks"},
    "matei_zaharia": {"name": "Matei Zaharia", "company": "Databricks"},
}


def search_and_extract(exa: Exa, query: str, source_type: str, **kwargs) -> list[dict]:
    """Search Exa and extract content."""
    try:
        results = exa.search_and_contents(
            query=query,
            type="auto",
            text=True,
            **kwargs,
        )
        return [
            {
                "text": (r.text or "")[:2000],
                "url": r.url or "",
                "title": r.title or "",
                "source_type": source_type,
                "published_date": r.published_date,
            }
            for r in results.results
            if r.text and len(r.text.strip()) > 100
        ]
    except Exception as e:
        print(f"  Error in {source_type} search: {e}")
        return []


def fetch_news(exa: Exa, name: str) -> list[dict]:
    """Fetch news articles about the author."""
    print(f"  Fetching news...")
    return search_and_extract(
        exa,
        f'"{name}" interview OR announced OR said',
        "news",
        num_results=15,
        category="news",
    )


def fetch_interviews(exa: Exa, name: str) -> list[dict]:
    """Fetch interviews with the author."""
    print(f"  Fetching interviews...")
    return search_and_extract(
        exa,
        f'"{name}" interview podcast conversation Q&A',
        "interview",
        num_results=10,
    )


def fetch_company_content(exa: Exa, name: str, company: str) -> list[dict]:
    """Fetch company-related content."""
    print(f"  Fetching company content...")
    return search_and_extract(
        exa,
        f'"{company}" {name} CEO blog announcement',
        "company",
        num_results=10,
    )


def fetch_podcasts(exa: Exa, name: str) -> list[dict]:
    """Fetch podcast appearances."""
    print(f"  Fetching podcasts...")
    return search_and_extract(
        exa,
        f'"{name}" podcast episode',
        "podcast",
        num_results=8,
        include_domains=["youtube.com", "spotify.com", "podcasts.apple.com"],
    )


def build_context(author: str, info: dict, exa: Exa) -> dict:
    """Build rich context for an author."""
    name = info["name"]
    company = info["company"]

    print(f"Building context for {name} ({author})...")

    context = {
        "author": author,
        "updated_at": datetime.now().isoformat(),
        "news": fetch_news(exa, name),
        "interviews": fetch_interviews(exa, name),
        "company": fetch_company_content(exa, name, company),
        "podcasts": fetch_podcasts(exa, name),
    }

    total = sum(len(context[k]) for k in ["news", "interviews", "company", "podcasts"])
    print(f"  Total: {total} items")

    return context


def save_context(context: dict) -> None:
    """Save context to JSON file."""
    author = context["author"]
    filepath = CONTEXT_DIR / f"{author}.json"

    with open(filepath, "w") as f:
        json.dump(context, f, indent=2)

    print(f"  Saved to {filepath.name}")


def main():
    if not EXA_API_KEY:
        print("Error: EXA_API_KEY not set")
        sys.exit(1)

    exa = Exa(api_key=EXA_API_KEY)
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

    for author, info in AUTHORS.items():
        context = build_context(author, info, exa)
        save_context(context)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make the script executable**

Run: `chmod +x /Users/shydev/mini-projects/writer-profile/scripts/scrape_context.py`

- [ ] **Step 3: Run the script to populate context**

Run: `cd /Users/shydev/mini-projects/writer-profile && EXA_API_KEY=d36e3a01-90c5-4e17-a9f7-ee2ac59f521d python scripts/scrape_context.py`
Expected: Context files created in `data/context/`

- [ ] **Step 4: Verify context files were created**

Run: `ls -la /Users/shydev/mini-projects/writer-profile/data/context/`
Expected: JSON files for each author

- [ ] **Step 5: Commit**

```bash
git add scripts/scrape_context.py data/context/
git commit -m "feat: add context scraper and populate rich context"
```

---

### Task 4: Update Generator to Use Rich Context

**Files:**
- Modify: `packages/api/src/writer_api/services/generator.py`

- [ ] **Step 1: Update generator to fetch from context store and multiple sources**

Replace the entire file with:

```python
from __future__ import annotations

from typing import AsyncGenerator

from writer_api.models.requests import GenerateRequest, RevoiceRequest
from writer_api.models.responses import GenerateResponse, Source
from writer_api.models.voice import VoiceProfile
from writer_api.prompts.templates import build_generator_prompt, build_revoice_prompt
from writer_api.services.context_store import ContextStore
from writer_api.services.exa_retriever import ExaRetriever, RetrievedContent
from writer_api.services.llm import get_llm_client


class GeneratorService:
    def __init__(self) -> None:
        self._retriever = ExaRetriever()
        self._context_store = ContextStore()
        self._llm = get_llm_client()

    def _get_cached_context(
        self, author: str, topic: str, max_per_type: int = 2
    ) -> list[RetrievedContent]:
        """Get relevant context from cache."""
        context = self._context_store.load(author)
        if not context:
            return []

        results: list[RetrievedContent] = []
        topic_lower = topic.lower()

        for source_list, source_type in [
            (context.news, "news"),
            (context.interviews, "interview"),
            (context.company, "company"),
            (context.podcasts, "podcast"),
        ]:
            relevant = [
                item
                for item in source_list
                if topic_lower in item.text.lower() or topic_lower in item.title.lower()
            ][:max_per_type]

            if not relevant and source_list:
                relevant = source_list[:1]

            for item in relevant:
                results.append(
                    RetrievedContent(
                        text=item.text,
                        url=item.url,
                        title=item.title,
                        source_type=source_type,
                        published_date=None,
                    )
                )

        return results

    def generate(self, request: GenerateRequest, profile: VoiceProfile) -> GenerateResponse:
        author_name = profile.author.replace("_", " ").title()

        platform_refs = self._retriever.search_for_generation(
            author_name=author_name,
            platform=request.platform,
            topic=request.topic,
            k=3,
        )

        topic_refs = self._retriever.search_topic_context(
            author_name=author_name,
            topic=request.topic,
            max_results=3,
        )

        cached_refs = self._get_cached_context(
            author=profile.author,
            topic=request.topic,
            max_per_type=2,
        )

        all_refs = platform_refs + topic_refs + cached_refs
        seen_urls = set()
        unique_refs = []
        for ref in all_refs:
            if ref.url not in seen_urls:
                seen_urls.add(ref.url)
                unique_refs.append(ref)

        ref_dicts = [{"text": r.text, "source_type": r.source_type} for r in unique_refs]

        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
            word_limit=request.word_limit,
        )

        response = self._llm.complete(system=system, user=user)
        text = response.text.strip().strip('"').strip("'")

        sources = [
            Source(
                title=r.title or r.url,
                url=r.url,
                source_type=r.source_type,
            )
            for r in unique_refs
            if r.url
        ]

        return GenerateResponse(
            text=text,
            author=request.author,
            platform=request.platform,
            validation_ok=True,
            sources_used=len(unique_refs),
            sources=sources,
        )

    async def generate_stream(
        self, request: GenerateRequest, profile: VoiceProfile
    ) -> AsyncGenerator[dict, None]:
        """Generate a post with streaming progress updates."""
        author_name = profile.author.replace("_", " ").title()

        yield {"step": "searching", "message": "Searching social media..."}

        platform_refs = self._retriever.search_for_generation(
            author_name=author_name,
            platform=request.platform,
            topic=request.topic,
            k=3,
        )

        yield {"step": "searching", "message": "Searching topic context..."}

        topic_refs = self._retriever.search_topic_context(
            author_name=author_name,
            topic=request.topic,
            max_results=3,
        )

        yield {"step": "searching", "message": "Loading cached context..."}

        cached_refs = self._get_cached_context(
            author=profile.author,
            topic=request.topic,
            max_per_type=2,
        )

        all_refs = platform_refs + topic_refs + cached_refs
        seen_urls = set()
        unique_refs = []
        for ref in all_refs:
            if ref.url not in seen_urls:
                seen_urls.add(ref.url)
                unique_refs.append(ref)

        sources = [
            {"title": r.title or r.url, "url": r.url, "source_type": r.source_type}
            for r in unique_refs
            if r.url
        ]

        yield {
            "step": "sources_found",
            "message": f"Found {len(unique_refs)} sources",
            "sources": sources,
        }

        yield {"step": "generating", "message": "Generating post with AI..."}

        ref_dicts = [{"text": r.text, "source_type": r.source_type} for r in unique_refs]

        system, user = build_generator_prompt(
            profile=profile,
            topic=request.topic,
            angle=request.angle or "",
            references=ref_dicts,
            virality=request.virality,
            word_limit=request.word_limit,
        )

        response = self._llm.complete(system=system, user=user)
        text = response.text.strip().strip('"').strip("'")

        yield {
            "step": "complete",
            "message": "Generation complete!",
            "result": {
                "text": text,
                "author": request.author,
                "platform": request.platform.value,
                "validation_ok": True,
                "sources_used": len(unique_refs),
                "sources": sources,
            },
        }

    def revoice(self, request: RevoiceRequest, profile: VoiceProfile) -> GenerateResponse:
        system, user = build_revoice_prompt(profile=profile, edited_draft=request.edited_draft)

        response = self._llm.complete(system=system, user=user)

        return GenerateResponse(
            text=response.text.strip(),
            author=request.author,
            platform=request.platform,
            validation_ok=True,
        )
```

- [ ] **Step 2: Verify the module compiles**

Run: `cd /Users/shydev/mini-projects/writer-profile/packages/api && uv run python -c "from writer_api.services.generator import GeneratorService; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/writer_api/services/generator.py
git commit -m "feat(api): integrate rich context sources in generator"
```

---

### Task 5: Copy Context to API Package and Deploy

**Files:**
- No new files

- [ ] **Step 1: Copy context data to API package**

```bash
cp -r /Users/shydev/mini-projects/writer-profile/data/context /Users/shydev/mini-projects/writer-profile/packages/api/data/
```

- [ ] **Step 2: Update Dockerfile to include context**

Edit `packages/api/Dockerfile` to add:

After `COPY data/ data/` line, the data directory already includes both profiles and context since we copied them.

No change needed if the data/ directory structure is:
```
data/
  profiles/
  context/
```

- [ ] **Step 3: Deploy API to Coolify**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/api
# DEPLOY: pushed to main → Coolify auto-builds (project: cadence)
```

- [ ] **Step 4: Wait and test**

```bash
sleep 45 && curl -s "https://coolify-backend/api/generate/stream" \
  -X POST -H "Content-Type: application/json" \
  -d '{"author":"sam_altman","platform":"linkedin","topic":"AI safety"}' | head -20
```

Expected: Multiple source types in the response (news, interview, company, etc.)

- [ ] **Step 5: Rebuild and deploy frontend**

```bash
cd /Users/shydev/mini-projects/writer-profile/packages/web
rm -rf .next out
NEXT_OUTPUT=export npm run build
npx wrangler pages deploy out --project-name=writer-profile --commit-dirty=true
```

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: integrate rich context sources for post generation"
```
