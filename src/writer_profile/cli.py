from __future__ import annotations

import json
from pathlib import Path

import typer

from writer_profile.config import Settings
from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import Idea, Platform
from writer_profile.eval.samples import ARCHETYPE_IDEAS, write_samples_sheet
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.extractor import build_voice_profile
from writer_profile.voice.store import VoiceProfileStore

app = typer.Typer(help="CEO Voice Agent — style-aware post generator for X and LinkedIn.")
profile_app = typer.Typer(help="Build and inspect voice profiles.")
app.add_typer(profile_app, name="profile")


def _pipeline(settings: Settings) -> GenerationPipeline:
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    profiles = VoiceProfileStore(root=settings.profiles_path)
    hooks = HookLibrary.load(settings.hooks_path)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    return GenerationPipeline(
        store=store,
        profiles=profiles,
        hooks=hooks,
        llm=llm,
        writing_model=settings.writing_model,
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
        hook_suggestion_k=settings.hook_suggestion_k,
    )


@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, readable=True, help="JSONL of posts"),
    author: str = typer.Option(..., help="Canonical author id (e.g. ali_ghodsi)"),
) -> None:
    """Ingest a JSONL corpus of past posts into the exemplar store."""
    settings = Settings()
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    count = ingest_file(
        path=path, store=store, llm=llm,
        classifier_model=settings.classifier_model,
        author=author,
    )
    typer.echo(f"ingested {count} posts for {author} into {settings.chroma_path}")


@profile_app.command("build")
def profile_build(
    author: str = typer.Option(..., help="Canonical author id"),
    platform: Platform = typer.Option(..., case_sensitive=False),
    source: Path = typer.Option(..., exists=True, readable=True,
                                help="JSONL of posts for this author+platform"),
) -> None:
    """Build a VoiceProfile from a JSONL of posts."""
    settings = Settings()
    posts = [
        p for p in load_posts_jsonl(source)
        if p.platform is platform and p.author == author
    ]
    if not posts:
        typer.echo(
            f"error: no posts matched author={author} platform={platform.value}",
            err=True,
        )
        raise typer.Exit(2)

    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    profile = build_voice_profile(
        author=author, platform=platform, posts=posts,
        llm=llm, model=settings.writing_model,
    )
    store = VoiceProfileStore(root=settings.profiles_path)
    path = store.save(profile)
    typer.echo(f"profile saved: {path} (based on {len(posts)} posts)")


@profile_app.command("show")
def profile_show(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
) -> None:
    """Print a saved VoiceProfile as JSON."""
    settings = Settings()
    store = VoiceProfileStore(root=settings.profiles_path)
    profile = store.load(author=author, platform=platform)
    typer.echo(profile.model_dump_json(indent=2))


@profile_app.command("list")
def profile_list() -> None:
    """List all saved profiles."""
    settings = Settings()
    store = VoiceProfileStore(root=settings.profiles_path)
    entries = store.list_profiles()
    for author, platform in sorted(entries):
        typer.echo(f"{author}\t{platform.value}")


@app.command()
def generate(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    topic: str = typer.Option(..., help="Topic / subject of the post"),
    angle: str = typer.Option("", help="Narrative direction / angle"),
    virality: float = typer.Option(
        0.15, min=0.0, max=1.0,
        help="Strength of virality hook injection (0-1)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip LLM calls, echo config."),
) -> None:
    """Generate a post."""
    settings = Settings()

    if dry_run:
        typer.echo(json.dumps({
            "author": author, "platform": platform.value,
            "topic": topic, "angle": angle, "virality": virality,
            "writing_model": settings.writing_model, "dry_run": True,
        }))
        raise typer.Exit(0)

    pipe = _pipeline(settings)
    draft = pipe.generate(
        author=author, platform=platform,
        idea=Idea(topic=topic, angle=angle),
        virality_strength=virality,
    )
    typer.echo(draft.text)
    if not draft.validation_ok:
        typer.echo(f"[warning] validator issues: {draft.validation_issues}", err=True)


@app.command()
def revoice(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    draft_file: Path = typer.Option(..., exists=True, readable=True,
                                    help="Plain text file containing the edited draft"),
) -> None:
    """Re-voice an edited draft."""
    settings = Settings()
    pipe = _pipeline(settings)
    edited = draft_file.read_text()
    out = pipe.revoice(author=author, platform=platform, edited_draft=edited)
    typer.echo(out.text)
    if not out.validation_ok:
        typer.echo(f"[warning] validator issues: {out.validation_issues}", err=True)


@app.command()
def samples(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    out_dir: Path = typer.Option(Path("./eval"), help="Output directory for sheets"),
    virality: float = typer.Option(0.15, min=0.0, max=1.0),
) -> None:
    """Generate one post per topic archetype for manual scoring."""
    settings = Settings()
    pipe = _pipeline(settings)
    results: list[tuple[str, str]] = []
    for idea in ARCHETYPE_IDEAS:
        d = pipe.generate(
            author=author, platform=platform, idea=idea,
            virality_strength=virality,
        )
        results.append((idea.topic, d.text))
    path = write_samples_sheet(
        root=out_dir, author=author, platform=platform, samples=results
    )
    typer.echo(f"wrote rubric sheet: {path}")


@app.command()
def evaluate(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    candidates_file: Path = typer.Option(..., exists=True, readable=True,
                                         help="JSONL with {candidate: str} per line"),
    references_file: Path = typer.Option(..., exists=True, readable=True,
                                         help="JSONL of real Posts by the author"),
    out_file: Path = typer.Option(Path("./eval/scores.jsonl")),
) -> None:
    """Run LLM-as-judge over candidate posts against reference corpus."""
    settings = Settings()
    references = load_posts_jsonl(references_file)
    references = [
        p for p in references if p.author == author and p.platform is platform
    ][:20]
    if not references:
        typer.echo("error: no reference posts matched author+platform", err=True)
        raise typer.Exit(2)

    from writer_profile.eval.judge import score_post

    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with (
        candidates_file.open("r", encoding="utf-8") as fin,
        out_file.open("w", encoding="utf-8") as fout,
    ):
        for line in fin:
            line = line.strip()
            if not line:
                continue
            cand = json.loads(line)["candidate"]
            score = score_post(
                author=author, platform=platform, candidate=cand,
                references=references, llm=llm, model=settings.judge_model,
            )
            fout.write(json.dumps({
                "candidate": cand,
                "voice_fidelity": score.voice_fidelity,
                "voice_reasoning": score.voice_reasoning,
                "naturalness": score.naturalness,
                "naturalness_reasoning": score.naturalness_reasoning,
                "ai_tics": score.ai_tics,
            }) + "\n")
    typer.echo(f"wrote scores: {out_file}")


if __name__ == "__main__":
    app()
