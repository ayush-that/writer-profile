from __future__ import annotations

import streamlit as st

from writer_profile.config import Settings
from writer_profile.corpus.models import Idea, Platform
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.store import VoiceProfileStore


@st.cache_resource
def get_pipeline() -> GenerationPipeline:
    settings = Settings()
    embedder = Embedder(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    profiles = VoiceProfileStore(root=settings.profiles_path)
    hooks = HookLibrary.load(settings.hooks_path)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    return GenerationPipeline(
        store=store, profiles=profiles, hooks=hooks, llm=llm,
        writing_model=settings.writing_model,
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
        hook_suggestion_k=settings.hook_suggestion_k,
    )


def main() -> None:
    st.set_page_config(page_title="CEO Voice Agent", layout="wide")
    st.title("CEO Voice Agent")

    pipe = get_pipeline()
    profiles = VoiceProfileStore(root=Settings().profiles_path)
    available = profiles.list_profiles()
    if not available:
        st.warning("No voice profiles found. Run `writer profile build` first.")
        st.stop()

    authors = sorted({a for a, _ in available})
    author = st.selectbox("CEO", authors)
    platforms_for_author = [p for a, p in available if a == author]
    platform_str = st.selectbox(
        "Platform",
        [p.value for p in platforms_for_author],
    )
    platform = Platform(platform_str)

    topic = st.text_input("Topic", placeholder="databricks acquires tabular")
    angle = st.text_area(
        "Angle / narrative direction",
        height=100,
        placeholder="this validates the open-source approach to data infra",
    )
    virality = st.slider("Virality strength", 0.0, 1.0, 0.15, 0.05)

    if "draft" not in st.session_state:
        st.session_state.draft = ""

    col_gen, col_rev = st.columns(2)

    with col_gen:
        if st.button("Generate", type="primary", disabled=not topic):
            with st.spinner("Generating..."):
                out = pipe.generate(
                    author=author, platform=platform,
                    idea=Idea(topic=topic, angle=angle),
                    virality_strength=virality,
                )
            st.session_state.draft = out.text
            if not out.validation_ok:
                st.warning(f"Validator issues: {out.validation_issues}")

    edited = st.text_area(
        "Draft (edit freely)", value=st.session_state.draft, height=300,
    )

    with col_rev:
        if st.button("Re-voice edits", disabled=not edited.strip()):
            with st.spinner("Revoicing..."):
                out = pipe.revoice(
                    author=author, platform=platform, edited_draft=edited,
                )
            st.session_state.draft = out.text
            st.rerun()

    st.caption(
        "Tip: edit the draft above, then click 'Re-voice edits' to re-apply the "
        "author's voice while keeping your structure."
    )


if __name__ == "__main__":
    main()
