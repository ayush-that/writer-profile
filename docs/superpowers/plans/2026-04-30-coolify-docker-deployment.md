# Coolify Docker Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Containerize FastAPI backend and Next.js frontend for deployment on Coolify self-hosted PaaS.

**Architecture:** Two Docker containers (api + web) orchestrated via docker-compose. The Next.js frontend proxies `/api/*` requests to the FastAPI backend via internal Docker networking. Both services share a `data/` volume for profiles and hooks.

**Tech Stack:** Docker, docker-compose, Python 3.13 + uv, Node 20 + pnpm, FastAPI, Next.js 16

---

## File Structure

```
writer-profile/
├── Dockerfile.api          # FastAPI backend container
├── Dockerfile.web          # Next.js frontend container
├── docker-compose.yml      # Orchestration for both services
├── docker-compose.prod.yml # Production overrides
├── .dockerignore           # Exclude unnecessary files
├── packages/web/
│   └── next.config.js      # Update API proxy for Docker networking
└── data/                   # Mounted as volume (profiles, hooks, scraped data)
```

---

### Task 1: Create .dockerignore

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore file**

```bash
cat > .dockerignore << 'EOF'
# Dependencies
node_modules/
.venv/
__pycache__/
*.pyc

# Build outputs
.next/
.open-next/
dist/
build/
*.egg-info/

# Dev files
.git/
.github/
.vscode/
*.md
docs/
tests/

# Environment
.env
.env.local
.env*.local
.dev.vars

# Misc
.DS_Store
*.log
.chroma/
EOF
```

- [ ] **Step 2: Verify file created**

Run: `cat .dockerignore | head -10`
Expected: Shows first 10 lines of ignore patterns

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore for Docker builds"
```

---

### Task 2: Create FastAPI Backend Dockerfile

**Files:**
- Create: `Dockerfile.api`

- [ ] **Step 1: Create Dockerfile.api**

```bash
cat > Dockerfile.api << 'EOF'
FROM python:3.13-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# Copy data directory (profiles, hooks)
COPY data/ ./data/

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uv", "run", "uvicorn", "writer_profile.api:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

- [ ] **Step 2: Test Docker build locally**

Run: `docker build -f Dockerfile.api -t writer-profile-api:local .`
Expected: Build completes successfully

- [ ] **Step 3: Test container runs**

Run: `docker run --rm -p 8000:8000 --env-file .env writer-profile-api:local &`
Wait 5 seconds, then: `curl http://localhost:8000/api/profiles | head -c 100`
Expected: Returns JSON with profiles list

- [ ] **Step 4: Stop test container**

Run: `docker stop $(docker ps -q --filter ancestor=writer-profile-api:local)`

- [ ] **Step 5: Commit**

```bash
git add Dockerfile.api
git commit -m "feat: add Dockerfile for FastAPI backend"
```

---

### Task 3: Create Next.js Frontend Dockerfile

**Files:**
- Create: `Dockerfile.web`

- [ ] **Step 1: Create Dockerfile.web**

```bash
cat > Dockerfile.web << 'EOF'
FROM node:20-alpine AS base

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

FROM base AS deps
WORKDIR /app

# Copy package files
COPY packages/web/package.json packages/web/pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app

# Copy deps from previous stage
COPY --from=deps /app/node_modules ./node_modules
COPY packages/web/ ./

# Set API URL for build time (will be overridden at runtime)
ENV NEXT_PUBLIC_API_URL=http://api:8000

# Build Next.js
RUN pnpm build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built assets
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
EOF
```

- [ ] **Step 2: Update next.config.js for standalone output**

```javascript
// packages/web/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.API_URL
          ? `${process.env.API_URL}/api/:path*`
          : "http://api:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
```

- [ ] **Step 3: Test Docker build locally**

Run: `docker build -f Dockerfile.web -t writer-profile-web:local .`
Expected: Build completes successfully

- [ ] **Step 4: Commit**

```bash
git add Dockerfile.web packages/web/next.config.js
git commit -m "feat: add Dockerfile for Next.js frontend with standalone output"
```

---

### Task 4: Create docker-compose.yml

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create docker-compose.yml**

```bash
cat > docker-compose.yml << 'EOF'
version: "3.8"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: writer-profile-api
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/profiles"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  web:
    build:
      context: .
      dockerfile: Dockerfile.web
    container_name: writer-profile-web
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://api:8000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

networks:
  default:
    name: writer-profile-network
EOF
```

- [ ] **Step 2: Test docker-compose builds**

Run: `docker-compose build`
Expected: Both images build successfully

- [ ] **Step 3: Test docker-compose up**

Run: `docker-compose up -d`
Wait 10 seconds, then: `curl http://localhost:3000`
Expected: Returns HTML page

- [ ] **Step 4: Check API proxy works**

Run: `curl http://localhost:3000/api/profiles | head -c 100`
Expected: Returns JSON with profiles (proxied through Next.js to FastAPI)

- [ ] **Step 5: Tear down**

Run: `docker-compose down`

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose for local dev and Coolify deployment"
```

---

### Task 5: Create Production docker-compose Override

**Files:**
- Create: `docker-compose.prod.yml`

- [ ] **Step 1: Create docker-compose.prod.yml**

```bash
cat > docker-compose.prod.yml << 'EOF'
version: "3.8"

services:
  api:
    image: ${REGISTRY:-ghcr.io}/${IMAGE_PREFIX:-writer-profile}/api:${TAG:-latest}
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      - CHROMA_API_KEY=${CHROMA_API_KEY}
      - CHROMA_HOST=${CHROMA_HOST}
      - CHROMA_TENANT=${CHROMA_TENANT}
      - CHROMA_DATABASE=${CHROMA_DATABASE}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - EXA_API_KEY=${EXA_API_KEY}

  web:
    image: ${REGISTRY:-ghcr.io}/${IMAGE_PREFIX:-writer-profile}/web:${TAG:-latest}
    build:
      context: .
      dockerfile: Dockerfile.web
    labels:
      - "coolify.managed=true"
EOF
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "feat: add production docker-compose override for Coolify"
```

---

### Task 6: Create Environment Template

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Create .env.example**

```bash
cat > .env.example << 'EOF'
# Required API Keys
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
EXA_API_KEY=...

# Optional: ChromaDB Cloud (if not using local)
CHROMA_API_KEY=
CHROMA_HOST=
CHROMA_TENANT=
CHROMA_DATABASE=

# Optional: Other APIs
TWITTER_API_KEY=
OPENROUTER_API_KEY=
MISTRAL_API_KEY=
FAL_API_KEY=
EOF
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add .env.example for deployment reference"
```

---

### Task 7: Test Full Stack Locally

**Files:**
- None (testing only)

- [ ] **Step 1: Build fresh images**

Run: `docker-compose build --no-cache`
Expected: Both images build successfully

- [ ] **Step 2: Start services**

Run: `docker-compose up -d`
Expected: Both containers start

- [ ] **Step 3: Wait for healthy state**

Run: `docker-compose ps`
Expected: Both services show "Up" status, api shows "(healthy)"

- [ ] **Step 4: Test API directly**

Run: `curl http://localhost:8000/api/profiles`
Expected: JSON response with profiles

- [ ] **Step 5: Test frontend**

Run: `curl -s http://localhost:3000 | grep -o '<title>.*</title>'`
Expected: Returns `<title>Cadence</title>` or similar

- [ ] **Step 6: Test API proxy through frontend**

Run: `curl http://localhost:3000/api/profiles`
Expected: Same JSON response as Step 4

- [ ] **Step 7: Check logs for errors**

Run: `docker-compose logs --tail=20`
Expected: No error messages

- [ ] **Step 8: Tear down**

Run: `docker-compose down -v`

- [ ] **Step 9: Final commit**

```bash
git add -A
git commit -m "chore: complete Docker deployment setup for Coolify"
git push
```

---

## Coolify Deployment Instructions

After completing all tasks, deploy to Coolify:

1. **Push to Git** - Ensure all changes are pushed to your repository

2. **In Coolify Dashboard:**
   - Create new Project → Docker Compose
   - Connect your Git repository
   - Set branch to `main`
   - Coolify will auto-detect `docker-compose.yml`

3. **Configure Environment Variables:**
   - Add all variables from `.env.example`
   - Set `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `EXA_API_KEY` (required)
   - Set ChromaDB variables if using cloud

4. **Configure Domains:**
   - Set domain for `web` service (e.g., `cadence.yourdomain.com`)
   - API is internal-only (accessed via Docker network)

5. **Deploy** - Click Deploy and monitor logs

---

## Self-Review Checklist

- [x] **Spec coverage:** All requirements covered (Dockerfile.api, Dockerfile.web, docker-compose.yml, routing)
- [x] **Placeholder scan:** No TBD/TODO/placeholder text
- [x] **Type consistency:** File paths and commands are consistent throughout
- [x] **Data persistence:** data/ directory mounted as volume for profiles/hooks
- [x] **Environment handling:** .env.example provided, env_file in compose
- [x] **Health checks:** API has healthcheck, web depends on healthy API
- [x] **Security:** Non-root user in web container, no secrets in Dockerfiles
