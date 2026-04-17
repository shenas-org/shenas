"""LLM provider lookup.

All LLM calls go through the shenas.net proxy. The user must be signed
in (remote_token stored) for AI features to work.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm.backends import LLMProvider

log = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Looks up the current user's remote_token and returns a
    ShenasNetProvider that proxies through shenas.net.
    """
    from app.llm.backends import ShenasNetProvider

    model = os.environ.get("SHENAS_LLM_MODEL", "claude-sonnet-4-6")

    try:
        from app.database import current_user_id
        from app.local_users import LocalUser

        uid = current_user_id.get()
        if uid is not None:
            user = LocalUser.find(uid)
            if user and user.remote_token:
                return ShenasNetProvider(token=user.remote_token, model=model)  # type: ignore[return-value]
            log.debug("No remote_token for user_id=%s", uid)
    except Exception:
        log.exception("Failed to look up remote_token")

    msg = "Sign in to shenas.net first (Settings > Profile) to use AI features."
    raise RuntimeError(msg)
