# Automated CEO Data Scraping — Design Spec

## Summary

Add automated data collection to the CEO Voice Agent using Exa API for LinkedIn posts, YouTube video discovery, and news/interview content. Twitter/X data requires manual collection due to platform restrictions.

## Problem Statement

The current pipeline requires users to manually create JSONL files of CEO posts before ingestion. This creates friction and limits adoption. We need automated scraping that:

1. Collects LinkedIn posts directly from CEO profiles
2. Discovers and transcribes YouTube interviews/talks
3. Gathers news articles and blog posts for context
4. Outputs data in the existing JSONL format for seamless integration

## Evaluation Results

Tested Exa and Firecrawl APIs on Ali Ghodsi (Databricks CEO):

| Capability | Exa | Firecrawl |
|------------|-----|-----------|
| LinkedIn posts | ✅ Found 10 posts via `linkedin.com/posts/*` | ❌ Not supported |
| YouTube videos | ✅ Finds videos with metadata | ❌ Not supported |
| News/interviews | ✅ Excellent coverage | ❌ Limited |
| Twitter/X | ❌ Cannot access feeds | ❌ Explicitly blocked |
| Blog posts | ✅ Finds authored content | ❌ Limited |

**Winner: Exa** — Only viable option for LinkedIn posts.

**Twitter limitation**: Neither API can scrape Twitter. Users must provide Twitter data manually via:
- Twitter archive export (Settings → Your Account → Download Archive)
- Twitter API v2 (requires developer approval)
- Manual copy-paste into JSONL

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI LAYER                                │
│                     writer scrape <author>                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SCRAPER MODULE                              │
│                src/writer_profile/scraper/                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   exa.py        │   youtube.py    │   models.py                 │
│   - search()    │   - download()  │   - ScrapedPost             │
│   - get_posts() │   - transcribe()│   - ScrapeResult            │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT (JSONL)                              │
│           data/<author>_linkedin.jsonl                           │
│           data/<author>_youtube.jsonl                            │
│           data/<author>_news.jsonl                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXISTING PIPELINE                              │
│              writer ingest → Chroma → generate                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Scraper Module (`src/writer_profile/scraper/`)

**models.py** — Data models for scraped content:
```python
class ScrapedPost(BaseModel):
    id: str
    author: str
    platform: Literal["linkedin", "youtube", "news"]
    text: str
    created_at: datetime
    url: str
    source: Literal["exa", "youtube_transcript"]

class ScrapeConfig(BaseModel):
    author_name: str           # "Ali Ghodsi"
    linkedin_handle: str       # "alighodsi"
    youtube_queries: list[str] # ["Ali Ghodsi interview", "Ali Ghodsi Databricks"]
    max_results_per_source: int = 50
```

**exa.py** — Exa API integration:
```python
class ExaScraper:
    def __init__(self, api_key: str): ...
    
    def scrape_linkedin_posts(self, handle: str, max_results: int = 50) -> list[ScrapedPost]:
        """Fetch LinkedIn posts using include_domains=['linkedin.com/posts']"""
        
    def scrape_youtube_videos(self, query: str, max_results: int = 20) -> list[dict]:
        """Find YouTube videos, return URLs + metadata for transcription"""
        
    def scrape_news(self, name: str, max_results: int = 30) -> list[ScrapedPost]:
        """Fetch news articles and interviews about the person"""
```

**youtube.py** — YouTube transcription:
```python
class YouTubeTranscriber:
    def __init__(self, whisper_model: str = "base"): ...
    
    def transcribe(self, video_url: str) -> str:
        """Download audio with yt-dlp, transcribe with Whisper"""
        
    def batch_transcribe(self, urls: list[str]) -> list[ScrapedPost]:
        """Transcribe multiple videos, return as posts"""
```

### 2. CLI Command (`writer scrape`)

```bash
# Scrape all available sources for a CEO
writer scrape "Ali Ghodsi" \
    --linkedin-handle alighodsi \
    --youtube-queries "Ali Ghodsi interview,Ali Ghodsi Databricks keynote" \
    --max-linkedin 50 \
    --max-youtube 10 \
    --max-news 30 \
    --output-dir ./data

# Output:
# data/ali_ghodsi_linkedin.jsonl (50 posts)
# data/ali_ghodsi_youtube.jsonl (10 transcripts)  
# data/ali_ghodsi_news.jsonl (30 articles)
```

### 3. Config Updates

Add to `Settings`:
```python
exa_api_key: SecretStr = Field(alias="EXA_API_KEY")
whisper_model: str = "base"  # tiny, base, small, medium, large
youtube_download_dir: str = "./data/youtube_cache"
```

### 4. Dependencies

Add to `pyproject.toml`:
```toml
"exa_py>=1.0.0",
"yt-dlp>=2024.0.0",
"openai-whisper>=20231117",
```

## Data Flow

1. **User runs**: `writer scrape "Ali Ghodsi" --linkedin-handle alighodsi`

2. **LinkedIn scraping**:
   - Exa searches `linkedin.com/posts/alighodsi*`
   - Returns post URLs + content previews
   - Extracts post text from markdown content
   - Outputs `data/ali_ghodsi_linkedin.jsonl`

3. **YouTube scraping** (if `--youtube-queries` provided):
   - Exa searches YouTube for the CEO
   - Returns video URLs + metadata
   - yt-dlp downloads audio
   - Whisper transcribes to text
   - Outputs `data/ali_ghodsi_youtube.jsonl`

4. **News scraping**:
   - Exa searches news category
   - Returns articles with CEO quotes
   - Outputs `data/ali_ghodsi_news.jsonl`

5. **User runs**: `writer ingest data/ali_ghodsi_*.jsonl --author ali_ghodsi`
   - Existing pipeline processes all JSONL files
   - Stores in Chroma for RAG

## Edge Cases

**Rate Limits**: Exa has rate limits. Implement exponential backoff and progress logging.

**LinkedIn Login Walls**: Some LinkedIn post content may be truncated. Accept partial content — it's still useful for voice profiling.

**YouTube Transcription Failures**: Some videos may fail (private, deleted, age-restricted). Log and skip, don't fail the whole batch.

**Duplicate Detection**: Exa may return the same post multiple times. Dedupe by URL before saving.

**Empty Results**: If no posts found, warn but don't error. The CEO may not have public LinkedIn posts.

## Testing Strategy

**Unit Tests**:
- Mock Exa API responses
- Test JSONL output format
- Test deduplication logic

**Integration Tests** (require API keys):
- Test against known CEO with public posts
- Verify output ingests correctly

**Manual Validation**:
- Scrape a CEO, ingest, generate a post
- Human review of voice fidelity

## Success Criteria

1. `writer scrape` command works for Ali Ghodsi and Matei Zaharia
2. LinkedIn posts are extracted with >80% of content intact
3. YouTube transcripts are accurate enough for voice profiling
4. Output JSONL ingests without errors
5. Generated posts show improved voice fidelity vs. no exemplars

## Out of Scope (V1)

- Twitter/X scraping (blocked by platforms)
- Podcast transcription (complex audio sourcing)
- Earnings call transcripts (different format, needs SEC parser)
- Real-time monitoring / scheduled scraping
- Multi-language support

## Security Considerations

- API keys stored as SecretStr, never logged
- YouTube downloads cached locally, auto-cleaned after transcription
- No PII extraction beyond public posts
- Respect robots.txt and rate limits

## Cost Estimate

Per CEO profile:
- Exa: ~100 API calls × $0.001 = $0.10
- Whisper (local): Free (CPU time)
- Total: ~$0.10 per CEO

## Timeline

- Implementation: 2-3 hours
- Testing: 1 hour
- Total: ~4 hours
