import os
import configparser
from typing import List, Dict, Any, Optional, Union

try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    print("Warning: 'openai' or 'pydantic' library not found. OpenAIClient functionality will be limited or unavailable.")

class AzureOpenAIClient:
    """
    A simple client for interacting with Azure OpenAI service for basic text completions.
    Reads configuration from config.ini.

    Configuration file should have a section 'openai_azure' with the following keys:
    - api_key: Your Azure OpenAI API key
    - endpoint: Your Azure OpenAI endpoint (e.g., https://your-resource-name.openai.azure.com/)
    - api_version: The API version to use (e.g., 2023-05-15)
    - deployment: The name of the Azure OpenAI deployment to use (e.g., gpt-35-turbo)
    """
    deployment: str

    def __init__(self, config_file: str = 'config.ini'):
        if not OPENAI_LIB_AVAILABLE:
            raise ImportError("OpenAI library is not installed. Cannot initialize AzureOpenAIClient.")
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found at '{os.path.abspath(config_file)}'.")
        
        config = configparser.ConfigParser()
        config.read(config_file)

        config_section = 'openai_azure'
        if config_section not in config:
            raise ValueError(f"Section '{config_section}' not found in '{config_file}'.")

        azure_cfg = config[config_section]
        api_key = azure_cfg.get('api_key')
        azure_endpoint = azure_cfg.get('endpoint')
        api_version = azure_cfg.get('api_version')
        self.deployment = azure_cfg.get('deployment')

        if not api_key: raise ValueError(f"Azure API key not found in '{config_section}'.")
        if not azure_endpoint: raise ValueError(f"Azure endpoint not found in '{config_section}'.")
        if not api_version: raise ValueError(f"Azure API version not found in '{config_section}'.")
        if not self.deployment: raise ValueError(f"Azure deployment name not found in '{config_section}'.")
        
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint
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
    """
    A simple client for interacting with the regular OpenAI service.
    Reads configuration from config.ini.

    Configuration file should have a section 'openai' with the following key:
    - api_key: Your OpenAI API key
    """
    def __init__(self, config_file: str = 'config.ini'):
        if not OPENAI_LIB_AVAILABLE:
            raise ImportError("OpenAI library is not installed. Cannot initialize OpenAIClient.")

        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found at '{os.path.abspath(config_file)}'.")
        
        config = configparser.ConfigParser()
        config.read(config_file)

        config_section = 'openai'
        if config_section not in config:
            raise ValueError(f"Section '{config_section}' not found in '{config_file}'.")
        
        std_config = config[config_section]
        api_key = std_config.get('api_key')
        
        if not api_key:
            raise ValueError("Standard OpenAI API key not found in config file.")
        
        self.client = OpenAI(api_key=api_key)
        print("Initialized OpenAIClient (using 'client.responses.create').")

    def get_completion(
        self,
        messages: Union[str, List[Dict[str, Any]]],
        model: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = 1.0,
    ) -> Optional[str]:
        """
        Gets a completion from the OpenAI API using `client.responses.create()`.
        Returns the raw text content of the LLM's final message.

        Args:
            model: The model name (e.g., "gpt-4.1", "gpt-4o").
            messages: The prompt, can be a string or list of message objects. Passed as 'input'.
            tools: Optional list of tools.
            temperature: Sampling temperature.

        Returns:
            The raw text content from the LLM's response, or None if an error occurs or content is empty.
        """
        print(f"--- OpenAIClient: Requesting completion from model: {model} via responses.create ---")

        try:
            create_params: Dict[str, Any] = {
                "model": model,
                "input": messages, # `client.responses.create` uses `input`
            }
            if tools: create_params["tools"] = tools
            if temperature: create_params['temperature'] = temperature

            response = self.client.responses.create(**create_params)
            print(response)
            # Try to extract text from ResponseOutputMessage
            try:
                llm_content = response.output[0].content[0].text
            except (AttributeError, IndexError) as e:
                # Handle the case where content or text is missing
                llm_content = None

            # If llm_content is not set, look for text in annotations
            if not llm_content:
                # Assuming 'response' holds the entire Response object
                # Navigate through the nested structure
                try:
                    # The 'output' attribute is a list. We're interested in the ResponseOutputMessage.
                    # In your example, it's the second item in the 'output' list.
                    output_message = None
                    for item in response.output:
                        # Check if the item has a 'content' attribute and if that content
                        # contains a ResponseOutputText object. This is a more robust way
                        # than relying purely on index if the order or number of items in
                        # response.output can change, as long as ResponseOutputMessage
                        # is uniquely identifiable or is the one containing the text.
                        # For your specific provided structure:
                        if hasattr(item, 'content') and item.content:
                            if hasattr(item.content[0], 'text'):
                                output_message = item
                                break
                    
                    if output_message:
                        # The 'content' attribute of ResponseOutputMessage is a list.
                        # The ResponseOutputText object is the first item in this list.
                        response_output_text = output_message.content[0]
                        
                        # Access the 'text' attribute
                        llm_content = response_output_text.text
                        print(llm_content)
                    else:
                        print("Could not find the text field in the expected structure.")

                except (AttributeError, IndexError, TypeError) as e:
                    print(f"An error occurred while trying to extract the text: {e}")
                    print("Please ensure the response object structure is as expected.")

            if llm_content is not None:
                print("--- OpenAIClient: Received content from 'responses.create' ---")
                return llm_content.strip()
            else:
                print(f"--- OpenAIClient Error: Could not extract text content from 'responses.create' output. Response object structure might be different than expected. Response: {response}")
                return None

        except AttributeError as ae:
            if "'OpenAI' object has no attribute 'responses'" in str(ae) or \
               "'Responses' object has no attribute 'create'" in str(ae):
                print("--- OpenAIClient Error: The 'responses.create' API "
                      "is not available in your version of the 'openai' library. "
                      "Consider upgrading or using client.chat.completions.create.")
            else:
                print(f"--- OpenAIClient Error: An AttributeError occurred: {ae} ---")
            import traceback
            traceback.print_exc()
            return None
        except Exception as e:
            print(f"--- OpenAIClient Error: An API error or other issue occurred with 'responses.create' ---")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_completion_with_search(
        self,
        messages: Union[str, List[Dict[str, Any]]],
        model: str = "gpt-4.1-mini",
        temperature: Optional[float] = 0.2,
    ) -> Optional[str]:
        return self.get_completion(
            messages=messages,
            model=model,
            tools=[{ "type": "web_search_preview" }],
            temperature=temperature
        )

if __name__ == "__main__":
    try:
        # azure_client = AzureOpenAIClient()
        # response = azure_client.get_completion("What is the capital of France?")
        # print(f"Azure Response: {response}")

        std_client = OpenAIClient()
        std_response = std_client.get_completion_with_search(
            messages="When is the F1 film being released?"
        )
        print(f"OpenAI Response: {std_response}")
    except Exception as e:
        print(f"Error during client operations: {e}")