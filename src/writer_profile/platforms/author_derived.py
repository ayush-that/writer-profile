from __future__ import annotations

from writer_profile.corpus.models import Platform
from writer_profile.platforms.base import Constraint
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import VoiceProfile

HASHTAG_TOLERANCE_THRESHOLD = 0.05  # if author uses hashtags in >=5% of posts, allow them


def constraint_for(profile: VoiceProfile) -> Constraint:
    if profile.platform is Platform.TWITTER:
        allow_hashtags = profile.stats.hashtag_rate >= HASHTAG_TOLERANCE_THRESHOLD
        avg_tags = profile.stats.avg_hashtags_per_post
        max_hashtags = max(1, round(avg_tags * 2)) if allow_hashtags else 0
        return TwitterConstraint(
            max_chars=280,
            allow_hashtags=allow_hashtags,
            require_lowercase=False,
            max_hashtags=max_hashtags if allow_hashtags else 3,
            max_urls=2,
        )
    if profile.platform is Platform.LINKEDIN:
        return LinkedInConstraint(max_chars=3000, max_words_per_nonempty_line=12)
    raise ValueError(f"no constraint mapping for platform {profile.platform}")
