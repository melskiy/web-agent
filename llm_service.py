import json
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
import openai
import instructor
import google.generativeai as genai
from google.generativeai import GenerativeModel


class LLMService:
    """
    Service for interacting with Large Language Models
    Uses instructor library for structured outputs
    """
    
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: str = "openai"
    ):
        self.model = model
        self.provider = provider
        
        if provider == "openai":
            # Set up OpenAI client with instructor for structured outputs
            if api_key:
                self.client = instructor.from_openai(
                    openai.OpenAI(api_key=api_key, base_url=base_url)
                )
            else:
                # If no API key provided, try to get from environment
                self.client = instructor.from_openai(openai.OpenAI())
        elif provider == "gemini":
            if api_key:
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(self.model)
            else:
                # If no API key provided, try to get from environment
                import os
                gemini_api_key = os.getenv("GEMINI_API_KEY")
                if gemini_api_key:
                    genai.configure(api_key=gemini_api_key)
                    self.client = genai.GenerativeModel(self.model)
                else:
                    raise ValueError("Gemini API key is required")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    async def get_completion(
        self,
        prompt: str,
        response_format: Optional[Type[BaseModel]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.1
    ) -> Any:
        """
        Get completion from LLM with optional structured output
        """
        try:
            if self.provider == "openai":
                if response_format:
                    # Use instructor for structured output
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        response_model=response_format,
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    return response
                else:
                    # Regular completion
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                    return response.choices[0].message.content
            elif self.provider == "gemini":
                # Prepare the prompt for Gemini
                if response_format:
                    # For structured output with Gemini, we need to include format instructions in the prompt
                    import json
                    schema = self._generate_json_schema(response_format)
                    formatted_prompt = f"{prompt}\n\nPlease respond in JSON format with the following structure:\n{json.dumps(schema, indent=2)}\n\nRespond with only the JSON object, no additional text."
                    
                    response = self.client.generate_content(
                        formatted_prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=schema,
                            max_output_tokens=max_tokens,
                            temperature=temperature
                        )
                    )
                    
                    # Parse the JSON response
                    response_text = response.text.strip()
                    # Remove any markdown code block markers
                    if response_text.startswith('```json'):
                        response_text = response_text[7:-3].strip()
                    elif response_text.startswith('```'):
                        response_text = response_text[3:-3].strip()
                    
                    parsed_response = json.loads(response_text)
                    return response_format(**parsed_response)
                else:
                    response = self.client.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature
                        )
                    )
                    return response.text
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise

    def _generate_json_schema(self, model: Type[BaseModel]) -> dict:
        """
        Generate JSON schema for the given Pydantic model
        """
        schema = model.model_json_schema()
        return schema


# Example structured response models
from pydantic import Field
from typing import Literal


class ActionModel(BaseModel):
    """
    Model for browser actions
    """
    action: Literal["click", "type", "scroll", "goto", "wait", "stop"]
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PlanModel(BaseModel):
    """
    Model for task plans
    """
    steps: list[ActionModel]
    description: str


class ReflectionModel(BaseModel):
    """
    Model for reflection responses
    """
    is_correct: bool
    feedback: str
    suggested_next_action: str