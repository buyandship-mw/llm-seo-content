import os
import json
from typing import List, Dict, Any, Optional, Union

from dotenv import load_dotenv
from utils.llm import extract_and_parse_json

load_dotenv()

try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    print("Warning: 'openai' or 'pydantic' library not found. OpenAIClient functionality will be limited or unavailable.")

class AzureOpenAIClient:
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

    def get_completion(
        self,
        prompt: str,
        system_message: Optional[str] = "You are a helpful assistant.",
        max_tokens: Optional[int] = None,
        temperature: float = 1.0
    ) -> str:
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
            return response_message.content
        except Exception as e:
            print(f"--- AzureOpenAIClient Error: An API error occurred ---")
            print(f"API Error: {e}")
            raise e

class OpenAIClient:
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

    def _extract_text_from_response(self, response: Any) -> Optional[str]:
        """
        Helper method to safely extract text content from the response.
        It checks for various known structures.
        """
        if not response or not hasattr(response, 'output') or not response.output:
            print(f"--- OpenAIClient Warning: Response object is empty or 'output' attribute is missing/empty. Response: {response} ---")
            return None

        if not isinstance(response.output, list):
            print(f"--- OpenAIClient Warning: response.output is not a list. Got: {type(response.output)} ---")
            return None

        # Iterate through items in response.output
        # This handles cases where the desired content might not be in the first item,
        # or if the first item doesn't conform to the primary expected structure.
        for item in response.output:
            if not item or not hasattr(item, 'content') or not item.content:
                continue # Move to the next item if this one is not structured as expected

            if not isinstance(item.content, list) or not item.content:
                continue # Move to the next item if item.content is not a non-empty list

            # We are typically interested in the first content block of an output item
            content_block = item.content[0]
            if not content_block:
                continue

            # Check for the 'text' attribute
            if hasattr(content_block, 'text') and isinstance(content_block.text, str):
                # Found text, return it.
                return content_block.text.strip()
            # else:
                # This branch means content_block exists but doesn't have a 'text' string attribute.
                # Could add more specific logging here if needed.
                # print(f"--- OpenAIClient Debug: Content block found but no 'text' attribute or not a string: {content_block}")

        # If no text was found after checking all items
        print(f"--- OpenAIClient Warning: Could not extract text content from any item in 'response.output' using known structures. Response: {response} ---")
        return None

    def get_completion(
        self,
        model: str,
        messages: Union[str, List[Dict[str, Any]]],
        temperature: Optional[float] = 1.0,
        tools: Optional[List[Dict]] = None,
    ) -> Optional[str]:
        """
        Gets a completion from the OpenAI API using `client.responses.create()`.
        Returns the raw text content of the LLM's final message.

        Args:
            model: The model name (e.g., "gpt-4.1", "gpt-4o").
            messages: The prompt, can be a string or list of message objects. Passed as 'input'.
            temperature: Sampling temperature. Use None to omit.
            tools: Optional list of tools.

        Returns:
            The raw text content from the LLM's response, or None if an error occurs or content is empty.
        """
        print(f"--- OpenAIClient: Requesting completion from model: {model} via responses.create ---")

        create_params: Dict[str, Any] = {
            "model": model,
            "input": messages, # `client.responses.create` uses `input`
        }
        if tools:
            create_params["tools"] = tools
        if temperature is not None: # Explicitly check for None, so 0.0 is a valid temperature
            create_params['temperature'] = temperature

        response: Optional[Any] = None
        try:
            # Check if client has 'responses' and 'responses.create' before calling
            if not hasattr(self.client, 'responses') or not hasattr(self.client.responses, 'create'):
                # This specific AttributeError was handled in the original code,
                # so we replicate that check before attempting the call.
                print("--- OpenAIClient Error: The 'responses.create' API "
                      "is not available in your version of the 'openai' library or client setup. "
                      "Consider upgrading or using client.chat.completions.create.")
                return None

            response = self.client.responses.create(**create_params)
            # It's good practice to log the raw response for debugging if issues occur
            # print(f"--- OpenAIClient Debug: Raw response object: {response} ---") # Potentially very verbose

            llm_content = self._extract_text_from_response(response)

            if llm_content is not None: # llm_content will be already stripped by the helper
                print("--- OpenAIClient: Received content from 'responses.create' ---")
                return llm_content
            else:
                # _extract_text_from_response already prints a warning,
                # but a more generic message here might also be useful.
                print(f"--- OpenAIClient Error: Failed to extract text content from 'responses.create' output. Full response logged above or in warnings.")
                return None

        except AttributeError as ae:
            # This block would catch other AttributeErrors not related to 'responses.create'
            # if they occurred during the setup or the call itself (less likely for 'create').
            print(f"--- OpenAIClient Error: An AttributeError occurred: {ae} ---")
            import traceback
            traceback.print_exc()
            return None
        except Exception as e: # Catch other potential API errors or unexpected issues
            print(f"--- OpenAIClient Error: An API error or other issue occurred with 'responses.create' ---")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_completion_with_search(
        self,
        model: str,
        messages: Union[str, List[Dict[str, Any]]],
        temperature: Optional[float] = 1.0,
    ) -> Optional[str]:
        return self.get_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            tools=[{ "type": "web_search_preview" }]
        )


if __name__ == "__main__":
    try:
        # azure_client = AzureOpenAIClient()
        # response = azure_client.get_completion("What is the capital of France?")
        # print(f"Azure Response: {response}")

        std_client = OpenAIClient()
        std_response = std_client.get_completion_with_search(
            model="gpt-4.1-mini",
            messages="When is the F1 film being released?"
        )
        print(f"OpenAI Response: {std_response}")
    except Exception as e:
        print(f"Error during client operations: {e}")