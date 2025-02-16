from typing import Dict, Type
import json
from abc import ABC, abstractmethod
import openai
from openai import AzureOpenAI, OpenAI
import anthropic
from ..config import LLMConfig

class LLMService(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str) -> Dict:
        """プロンプトからレスポンスを生成"""
        pass

    def _create_error_response(self, error_message: str) -> Dict:
        return {
            "response": {
                "message": f"エラーが発生しました: {error_message}",
                "tone": "error"
            },
            "analysis": {
                "extracted_requirements": [],
                "identified_constraints": [],
                "potential_risks": []
            },
            "next_steps": {
                "suggested_topics": [],
                "recommended_questions": []
            }
        }

    def _parse_response(self, response) -> Dict:
        try:
            if hasattr(response.choices[0], 'message'):
                content = response.choices[0].message.content
            else:
                content = response.choices[0].text
            return json.loads(content)
        except json.JSONDecodeError:
            return self._create_error_response("Failed to parse JSON response")
        except Exception as e:
            return self._create_error_response(f"Error parsing response: {str(e)}")

class AzureOpenAIService(LLMService):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.api_base
        )

    async def generate_response(self, prompt: str) -> Dict:
        try:
            response = await self._call_azure_openai(prompt)
            return self._parse_response(response)
        except Exception as e:
            return self._create_error_response(str(e))

    async def _call_azure_openai(self, prompt: str) -> Dict:
        response = self.client.chat.completions.create(
            model=self.config.deployment_name,
            messages=[
                {"role": "system", "content": "あなたは経験豊富なシステムアナリストとして、要件定義のサポートを行います。"},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"}
        )
        return response

class OpenAIService(LLMService):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key)

    async def generate_response(self, prompt: str) -> Dict:
        try:
            response = await self._call_openai(prompt)
            return self._parse_response(response)
        except Exception as e:
            return self._create_error_response(str(e))

    async def _call_openai(self, prompt: str) -> Dict:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "あなたは経験豊富なシステムアナリストとして、要件定義のサポートを行います。"},
                {"role": "user", "content": prompt}
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"}
        )
        return response

class AnthropicService(LLMService):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.api_key)

    async def generate_response(self, prompt: str) -> Dict:
        try:
            response = await self._call_anthropic(prompt)
            return self._parse_response(response)
        except Exception as e:
            return self._create_error_response(str(e))

    async def _call_anthropic(self, prompt: str) -> Dict:
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system="あなたは経験豊富なシステムアナリストとして、要件定義のサポートを行います。",
            messages=[{"role": "user", "content": prompt}]
        )
        return response

class LLMServiceFactory:
    _services: Dict[str, Type[LLMService]] = {
        "azure": AzureOpenAIService,
        "openai": OpenAIService,
        "anthropic": AnthropicService
    }

    @classmethod
    def create(cls, config: LLMConfig) -> LLMService:
        service_class = cls._services.get(config.provider.lower())
        if not service_class:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
        return service_class(config)

    @classmethod
    def register_service(cls, provider: str, service_class: Type[LLMService]):
        cls._services[provider.lower()] = service_class
