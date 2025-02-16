from typing import Optional, Dict
from dataclasses import dataclass
import os
import json

@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000

class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()

    def _get_default_config_path(self) -> str:
        config_dir = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        return os.path.join(config_dir, 'requirements-assistant', 'config.json')

    def _load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return self._create_default_config()

    def _create_default_config(self) -> Dict:
        config = {
            "llm": {
                "provider": "azure",
                "model": os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4'),
                "api_key": os.getenv('AZURE_OPENAI_API_KEY', ''),
                "api_base": os.getenv('AZURE_OPENAI_API_BASE', ''),
                "api_version": os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview'),
                "deployment_name": os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', ''),
                "temperature": float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                "max_tokens": int(os.getenv('OPENAI_MAX_TOKENS', '32000'))
            },
            "output": {
                "format": "markdown",
                "output_dir": "outputs"
            },
            "session": {
                "save_dir": "sessions",
                "autosave": True,
                "autosave_interval": 300
            },
            "debug": {
                "enabled": os.getenv('DEBUG', 'false').lower() == 'true',
                "log_level": os.getenv('LOG_LEVEL', 'INFO')
            }
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return config

    def get_llm_config(self) -> LLMConfig:
        llm_config = self.config.get('llm', {})
        return LLMConfig(
            provider=llm_config.get('provider', 'azure'),
            model=llm_config.get('model', 'gpt-4'),
            api_key=llm_config.get('api_key', ''),
            api_base=llm_config.get('api_base'),
            api_version=llm_config.get('api_version'),
            deployment_name=llm_config.get('deployment_name'),
            temperature=llm_config.get('temperature', 0.7),
            max_tokens=llm_config.get('max_tokens', 32000)
        )

    def update_llm_config(self, new_config: Dict) -> None:
        self.config['llm'].update(new_config)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_output_dir(self) -> str:
        return self.config.get('output', {}).get('output_dir', 'outputs')

    def get_session_config(self) -> Dict:
        return self.config.get('session', {})

    def get_debug_mode(self) -> bool:
        return self.config.get('debug', {}).get('enabled', False)

    def set_debug_mode(self, enabled: bool):
        if 'debug' not in self.config:
            self.config['debug'] = {}
        self.config['debug']['enabled'] = enabled
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
