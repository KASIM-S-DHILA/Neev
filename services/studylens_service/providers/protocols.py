"""Contracts for external providers.

Interfaces only. Nothing calls them yet.

ponytail: ``ProviderResponse.revision`` is required, not optional. That is the
whole point of the seam: an inlined Ollama call today cannot say which prompt
produced a result, and that gap is invisible until you try to reproduce it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence


class ProviderKind(Enum):
    """Where a provider runs. ``local`` means nothing leaves the machine."""

    GROQ = "groq"
    OLLAMA = "ollama"
    YOUTUBE = "youtube"
    LOCAL = "local"


@dataclass(frozen=True)
class ProviderCapability:
    """What a provider can currently do, as ``GET /vision`` and ``GET /audio`` report."""

    available: bool
    model: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class ProviderRequest:
    """One outbound call.

    ``kind`` decides which fields are meaningful. Credentials are never carried
    here: they stay in backend environment/request headers, and native helpers
    have ``GROQ_API_KEY`` and the local API token removed before launch.
    """

    kind: ProviderKind
    model: str
    prompt_revision: str
    """Required. Identifies the exact prompt text used."""

    payload: dict = field(default_factory=dict)
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class ProviderResponse:
    """One provider result, always attributable."""

    text: str
    model: str
    prompt_revision: str
    """Required, and must equal the request's revision."""

    input_sha256: str | None = None
    provider_metadata: dict = field(default_factory=dict)


class Provider(Protocol):
    """The contract one provider adapter implements."""

    def capability(self) -> ProviderCapability:
        """Report availability without making a request."""
        raise NotImplementedError

    def send(self, request: ProviderRequest) -> ProviderResponse:
        """Perform one bounded call. Must not follow redirects."""
        raise NotImplementedError

    def prompts(self) -> Sequence[str]:
        """Return the prompt revisions this provider can emit."""
        raise NotImplementedError


def prompts(kind: ProviderKind) -> Sequence[str]:
    """List known prompt revisions for one provider. Not implemented."""
    raise NotImplementedError