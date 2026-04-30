# Writer Profile

Generate authentic social media content in the voice of tech CEOs and thought leaders.

## Overview

Writer Profile is a style-aware content generation tool that creates Twitter/X and LinkedIn posts matching an author's unique voice. It uses:

- **Voice profiles** capturing lexical, structural, and tonal patterns from real posts
- **Exa search** to retrieve relevant context and recent writing samples
- **Claude Sonnet** for style-conditioned generation

## Architecture

```
writer-profile/
├── packages/
│   ├── api/          # FastAPI backend (Python)
│   └── web/          # Next.js frontend (React)
├── data/
│   └── profiles/     # Voice profiles (JSON)
└── docker-compose.yml
```

**Monorepo managed with Turborepo + pnpm.**

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- pnpm 9+
- uv (Python package manager)

### Setup

```bash
# Install dependencies
pnpm install
cd packages/api && uv sync

# Configure environment
cp .env.example .env
# Add your API keys to .env
```

Required API keys:
- `ANTHROPIC_API_KEY` - Claude API
- `EXA_API_KEY` - Exa search API

### Development

```bash
# Run both services
pnpm dev

# Or individually
pnpm api:dev   # API at http://localhost:8000
pnpm web:dev   # Web at http://localhost:3000
```

### Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/profiles` | List available voice profiles |
| POST | `/api/generate` | Generate content |
| POST | `/api/revoice` | Re-voice edited draft |

### Generate Request

```json
{
  "author": "sam_altman",
  "platform": "twitter",
  "topic": "why AGI timelines are shorter than expected",
  "angle": "contrarian but optimistic",
  "virality": 0.7
}
```

## Voice Profiles

Pre-built profiles for tech leaders:

| Author | Twitter | LinkedIn |
|--------|---------|----------|
| Sam Altman | x | x |
| Elon Musk | x | x |
| Satya Nadella | x | x |
| Patrick Collison | x | x |
| Guillermo Rauch | x | x |
| Brian Chesky | x | x |
| Dario Amodei | x | x |
| Aravind Srinivas | x | x |
| Tobi Lutke | x | x |
| Matei Zaharia | x | x |
| Ali Ghodsi | x | x |

Profiles are stored in `data/profiles/{author}__{platform}.json`.

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | - | Claude API key |
| `EXA_API_KEY` | Yes | - | Exa search key |
| `LLM_PROVIDER` | No | `anthropic` | LLM provider |
| `LLM_MODEL` | No | `claude-sonnet-4-6` | Model to use |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Allowed origins |

## Tech Stack

**Backend:**
- FastAPI
- Pydantic v2
- Anthropic SDK
- Exa Python SDK

**Frontend:**
- Next.js 16
- React 19
- Tailwind CSS
- Framer Motion

## License

MIT
