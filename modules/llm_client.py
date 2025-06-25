from typing import Any, Optional

class LLMClient:
    """Abstract base class for LLM clients."""

    def get_completion(self, *args: Any, **kwargs: Any) -> Optional[str]:
        """Return a completion from the model."""
        raise NotImplementedError

    @property
    def supports_web_search(self) -> bool:
        """Whether this client can utilize web search."""
        return False

    def get_completion_with_search(
        self,
        *,
        prompt: str,
        model: str,
        temperature: float | None = 1.0,
    ) -> Optional[str]:
        """Return a completion utilizing web search when supported."""
        raise NotImplementedError
