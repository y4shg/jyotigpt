"""Configuration domain service.

Runtime configuration lives on a single AppConfig instance attached to the
application state. Import/export round-trips through the config file; the
remaining operations mutate the live instance and echo the fresh values
back. The code-execution settings are read/written in one block, and tool
servers are re-verified against their upstream endpoints after any change.
"""

from typing import Any, Optional

from jyotigpt.config import AppConfig, get_config, save_config
from jyotigpt.utils.tools import get_tool_server_data, get_tool_servers_data

_CODE_EXECUTION_KEYS = (
    "ENABLE_CODE_EXECUTION",
    "CODE_EXECUTION_ENGINE",
    "CODE_EXECUTION_JUPYTER_URL",
    "CODE_EXECUTION_JUPYTER_AUTH",
    "CODE_EXECUTION_JUPYTER_AUTH_TOKEN",
    "CODE_EXECUTION_JUPYTER_AUTH_PASSWORD",
    "CODE_EXECUTION_JUPYTER_TIMEOUT",
)

_CODE_INTERPRETER_KEYS = (
    "ENABLE_CODE_INTERPRETER",
    "CODE_INTERPRETER_ENGINE",
    "CODE_INTERPRETER_PROMPT_TEMPLATE",
    "CODE_INTERPRETER_JUPYTER_URL",
    "CODE_INTERPRETER_JUPYTER_AUTH",
    "CODE_INTERPRETER_JUPYTER_AUTH_TOKEN",
    "CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD",
    "CODE_INTERPRETER_JUPYTER_TIMEOUT",
)


class ConfigService:
    def import_(self, config_data: dict) -> dict:
        save_config(config_data)
        return get_config()

    def export(self) -> dict:
        return get_config()

    def get_direct_connections(self, config: AppConfig) -> dict:
        return {"ENABLE_DIRECT_CONNECTIONS": config.ENABLE_DIRECT_CONNECTIONS}

    def set_direct_connections(self, config: AppConfig, enabled: bool) -> dict:
        config.ENABLE_DIRECT_CONNECTIONS = enabled
        return {"ENABLE_DIRECT_CONNECTIONS": config.ENABLE_DIRECT_CONNECTIONS}

    def get_tool_servers(self, config: AppConfig) -> dict:
        return {"TOOL_SERVER_CONNECTIONS": config.TOOL_SERVER_CONNECTIONS}

    async def set_tool_servers(self, state: Any, connections: list[dict]) -> dict:
        # `state` is the ASGI application state: the config instance plus the
        # derived TOOL_SERVERS cache refreshed against each server's endpoint.
        state.config.TOOL_SERVER_CONNECTIONS = connections
        state.TOOL_SERVERS = await get_tool_servers_data(connections)
        return {"TOOL_SERVER_CONNECTIONS": connections}

    async def verify_connection(self, token: Optional[str], url: str):
        return await get_tool_server_data(token, url)

    @staticmethod
    def _collect(config: AppConfig, keys: tuple[str, ...]) -> dict:
        return {key: getattr(config, key) for key in keys}

    def get_code_execution(self, config: AppConfig) -> dict:
        return {
            **self._collect(config, _CODE_EXECUTION_KEYS),
            **self._collect(config, _CODE_INTERPRETER_KEYS),
        }

    def set_code_execution(self, config: AppConfig, values: dict) -> dict:
        for key in (*_CODE_EXECUTION_KEYS, *_CODE_INTERPRETER_KEYS):
            setattr(config, key, values[key])
        return self.get_code_execution(config)

    def get_models(self, config: AppConfig) -> dict:
        return {
            "DEFAULT_MODELS": config.DEFAULT_MODELS,
            "MODEL_ORDER_LIST": config.MODEL_ORDER_LIST,
        }

    def set_models(self, config: AppConfig, values: dict) -> dict:
        config.DEFAULT_MODELS = values["DEFAULT_MODELS"]
        config.MODEL_ORDER_LIST = values["MODEL_ORDER_LIST"]
        return self.get_models(config)

    def set_suggestions(self, config: AppConfig, suggestions: list) -> list:
        config.DEFAULT_PROMPT_SUGGESTIONS = suggestions
        return config.DEFAULT_PROMPT_SUGGESTIONS

    def set_banners(self, config: AppConfig, banners: list) -> list:
        config.BANNERS = banners
        return config.BANNERS

    def get_banners(self, config: AppConfig) -> list:
        return config.BANNERS


configs = ConfigService()
