import os
import configparser
from openai import AzureOpenAI

class OpenAIClient:
    """
    A client for interacting with Azure OpenAI service.
    Reads configuration from config.ini.
    """
    def __init__(self, config_file='config.ini'):
        """
        Initializes the AzureOpenAI client with settings from the config file.

        Args:
            config_file (str): Path to the configuration file.
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

        config = configparser.ConfigParser()
        config.read(config_file)

        if 'azure_openai' not in config:
            raise ValueError("Section 'azure_openai' not found in config.ini.")

        azure_config = config['azure_openai']
        self.api_key = azure_config.get('api_key')
        self.azure_endpoint = azure_config.get('endpoint') # Changed from 'azure_endpoint'
        self.api_version = azure_config.get('api_version')
        self.model_deployment = azure_config.get('deployment') # Changed from 'model_deployment'

        if not self.api_key:
            raise ValueError("Key 'api_key' not found in [azure_openai] section of config.ini.")
        if not self.azure_endpoint:
            raise ValueError("Key 'endpoint' not found in [azure_openai] section of config.ini.")
        if not self.model_deployment:
            raise ValueError("Key 'deployment' not found in [azure_openai] section of config.ini.")
        if not self.api_version:
            # Fallback or specific default if desired, else raise error
            # For Azure, api_version is usually required.
            raise ValueError("Key 'api_version' not found in [azure_openai] section of config.ini.")

        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint
        )

    def get_completion(self, system_message_content: str, user_prompt_content: str) -> str:
        """
        Gets a completion from the Azure OpenAI model.

        Args:
            system_message_content (str): The content for the system message.
            user_prompt_content (str): The content for the user prompt.

        Returns:
            str: The content of the model's response.
            None: If an error occurs or the response is empty.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_deployment, # This uses the 'deployment' name from config.ini
                messages=[
                    {"role": "system", "content": system_message_content},
                    {"role": "user", "content": user_prompt_content}
                ]
            )
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                if message:
                    return message.content
                else:
                    print("Warning: Response choice message is empty.")
                    return None
            else:
                print("Warning: Received no choices in the response from the API.")
                # You might want to inspect the full response object here for more details
                # print(f"Full API response: {response.model_dump_json(indent=2)}")
                return None
        except Exception as e:
            print(f"An error occurred while calling the Azure OpenAI API: {e}")
            return None

# --- Example Usage ---
if __name__ == "__main__":
    try:
        ai_client = OpenAIClient() # Reads config.ini by default

        system_prompt = "You are an AI assistant that helps people find information accurately."
        user_query = "Who were the primary inventors of the transistor?"

        print(f"Sending prompt to deployment: {ai_client.model_deployment} at endpoint: {ai_client.azure_endpoint} using API version: {ai_client.api_version}")

        model_response = ai_client.get_completion(system_prompt, user_query)

        if model_response:
            print("\n--- Model Response ---")
            print(model_response)
            print("----------------------\n")
        else:
            print("Failed to get a response from the model.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure 'config.ini' exists in the same directory as the script.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")