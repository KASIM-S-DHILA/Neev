"""External model providers behind one interface.

Scaffolded in the Phase B4 architecture reset. **Not implemented.**

Today Groq, Ollama and YouTube clients are inlined in the modules that use them
(``cloud_vision.py``, ``cloud_audio.py``, ``visual.py``, ``youtube_helper.py``).
This package is the intended seam, not a refactor that has happened.

The reason it matters is provenance, not tidiness: Groq vision stores a
``prompt_version`` and ASR stores engine/config/model, but **Ollama stores only
model and text with no prompt revision**. A single interface forces every result
to record what produced it.

See ``docs/DECISIONS.md`` D14 and ``docs/PRIVACY_AND_DATA_FLOW.md``.
"""

from .protocols import (
    ProviderCapability,
    ProviderKind,
    ProviderRequest,
    ProviderResponse,
    Provider,
    prompts,
)

__all__ = [
    "Provider",
    "ProviderCapability",
    "ProviderKind",
    "ProviderRequest",
    "ProviderResponse",
    "prompts",
]