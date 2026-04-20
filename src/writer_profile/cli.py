from __future__ import annotations

import json
from pathlib import Path

import typer

from writer_profile.config import Settings
from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.models import Platform
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore

app = typer.Typer(help="Writer-profile: style-aware post generator for Twitter/X and LinkedIn.")


def _default_constraints() -> dict[Platform, object]:
    return {
        Platform.TWITTER: TwitterConstraint(),
        Platform.LINKEDIN: LinkedInConstraint(),
    }


@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, readable=True, help="JSONL of posts"),
) -> None:
    """Ingest a JSONL corpus of past posts into the exemplar store."""
    settings = Settings()
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    count = ingest_file(path=path, store=store, llm=llm, classifier_model=settings.classifier_model)
    typer.echo(f"ingested {count} posts into {settings.chroma_path}")


@app.command()
def generate(
    platform: Platform = typer.Option(..., case_sensitive=False),
    topic: str = typer.Option(..., help="What to write about"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not call the LLM; emit echoed config as JSON (for smoke tests).",
    ),
) -> None:
    """Generate a post for PLATFORM on TOPIC."""
    settings = Settings()

    if dry_run:
        typer.echo(
            json.dumps(
                {
                    "platform": platform.value,
                    "topic": topic,
                    "writing_model": settings.writing_model,
                    "dry_run": True,
                }
            )
        )
        raise typer.Exit(0)

    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    pipe = GenerationPipeline(
        store=store,
        llm=llm,
        writing_model=settings.writing_model,
        constraints=_default_constraints(),  # type: ignore[arg-type]
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
    )
    draft = pipe.generate(topic=topic, platform=platform)
    typer.echo(draft.text)
    if not draft.validation_ok:
        typer.echo(f"[warning] validator issues: {draft.validation_issues}", err=True)


if __name__ == "__main__":
    app()
