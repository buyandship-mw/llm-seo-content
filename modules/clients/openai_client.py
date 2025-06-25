import os
from typing import List, Dict, Any, Optional, Tuple, Union

from dotenv import load_dotenv
from .llm_client import LLMClient

load_dotenv()

try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    print("Warning: 'openai' or 'pydantic' library not found. OpenAIClient functionality will be limited or unavailable.")

class AzureOpenAIClient(LLMClient):
    """Client for Azure OpenAI using environment variables.

    Required environment variables:
      - ``AZURE_OPENAI_API_KEY``
      - ``AZURE_OPENAI_ENDPOINT``
      - ``AZURE_OPENAI_API_VERSION``
      - ``AZURE_OPENAI_DEPLOYMENT``
    """

    deployment: str

    def __init__(self) -> None:
        if not OPENAI_LIB_AVAILABLE:
            raise ImportError("OpenAI library is not installed. Cannot initialize AzureOpenAIClient.")

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        if not api_key:
            raise ValueError("Environment variable AZURE_OPENAI_API_KEY not set.")
        if not azure_endpoint:
            raise ValueError("Environment variable AZURE_OPENAI_ENDPOINT not set.")
        if not api_version:
            raise ValueError("Environment variable AZURE_OPENAI_API_VERSION not set.")
        if not self.deployment:
            raise ValueError("Environment variable AZURE_OPENAI_DEPLOYMENT not set.")

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
        )
        print(f"Initialized AzureOpenAIClient with deployment: {self.deployment}.")

    @property
    def supports_web_search(self) -> bool:
        return False

    def get_response(
        self,
        prompt: str,
        model: str,
        temperature: float = 1.0,
        *,
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = "You are a helpful assistant.",
        use_search: bool = False,
    ) -> Tuple[Any, Optional[str]]:
        """
        Gets a simple text completion from the Azure OpenAI service.

        Args:
            prompt: The user's text prompt.
            system_message: Content for the system message.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature.

        Returns:
            The text content of the LLM's response.
        
        Raises:
            Exception: If an error occurs during the API call or response processing.
        """
        if use_search:
            raise NotImplementedError("Search not supported by this client")

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        print(f"--- AzureOpenAIClient: Requesting completion from deployment: {self.deployment} ---")
        try:
            completion_params: Dict[str, Any] = {
                "model": self.deployment, # In Azure, 'model' is the deployment name
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                completion_params["max_tokens"] = max_tokens
            
            chat_completion = self.client.chat.completions.create(**completion_params)
            response_message = chat_completion.choices[0].message

            print("--- AzureOpenAIClient: Received completion ---")
            return chat_completion, response_message.content
        except Exception as e:
            print(f"--- AzureOpenAIClient Error: An API error occurred ---")
            print(f"API Error: {e}")
            raise e

class OpenAIClient(LLMClient):
    """Client for the standard OpenAI API using environment variables.

    Requires the ``OPENAI_API_KEY`` environment variable.
    """

    def __init__(self) -> None:
        if not OPENAI_LIB_AVAILABLE:
            raise ImportError("OpenAI library is not installed. Cannot initialize OpenAIClient.")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Environment variable OPENAI_API_KEY not set.")

        self.client = OpenAI(api_key=api_key)
        print("Initialized OpenAIClient (using 'client.responses.create').")

    @property
    def supports_web_search(self) -> bool:
        return True

    def _extract_text_from_response(self, response: Any) -> Optional[str]:
        """Extract text from OpenAI responses (including web search function outputs)."""
        if not response:
            print("--- OpenAIClient Warning: Empty response object ---")
            return None

        # If 'output' attribute is present and is a list
        if hasattr(response, "output") and response.output:
            for item in response.output:
                # Look for ResponseOutputMessage (has .content)
                content = getattr(item, "content", None)
                if content and isinstance(content, list):
                    # Each content item could be a ResponseOutputText
                    for c in content:
                        text = getattr(c, "text", None)
                        if text and isinstance(text, str):
                            return text.strip()
                # If just a plain text output (rare in this API, but just in case)
                if isinstance(item, str):
                    return item.strip()
        print("--- OpenAIClient Warning: Could not extract text content from response ---")
        return None

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
        """Return a tuple of raw response and extracted assistant text."""

        messages: List[Dict[str, Any]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        create_params: Dict[str, Any] = {
            "model": model,
            "input": messages,
        }
        if temperature is not None:
            create_params["temperature"] = temperature
        if max_tokens is not None:
            create_params["max_tokens"] = max_tokens

        if use_search:
            if not self.supports_web_search:
                raise NotImplementedError("Search not supported by this client")
            create_params["tools"] = [{"type": "web_search_preview"}]
            create_params["tool_choice"] = {"type": "web_search_preview"}

        response = self.client.responses.create(**create_params)
        text = self._extract_text_from_response(response)
        return response, text

    def web_search_occurred(self, response: Any) -> bool:
        if hasattr(response, "output") and response.output:
            for item in response.output:
                if getattr(item, "type", None) == "web_search_call":
                    return True
        return False

if __name__ == "__main__":
    try:
        std_client = OpenAIClient()
        # Use the refactored method that returns raw response and extracted text
        response, result = std_client.get_response(
            prompt="When is Maroon 5 coming to Pittsburgh in 2025? They just announced a new tour.",
            model="gpt-4.1-mini",
            use_search=True
        )

        if std_client.web_search_occurred(response):
            print(f"OpenAI Response: {result}")
        else:
            print("Web search was not invoked. Response rejected.")

    except Exception as e:
        print(f"Error during client operations: {e}")
