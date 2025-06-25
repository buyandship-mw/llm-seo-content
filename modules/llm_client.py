from typing import Any, Optional, Tuple

class LLMClient:
    """Abstract base class for LLM clients."""

    @property
    def supports_web_search(self) -> bool:
        """Whether this client can utilize web search."""
        return False

    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 1.0,
        *,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        use_search: bool = False,
    ) -> Tuple[Any, Optional[str]]:
        """Return a tuple of raw API response and extracted text."""
        raise NotImplementedError
