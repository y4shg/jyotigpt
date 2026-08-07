"""Tool domain service.

Tools are user-authored Python toolkit plugins plus servers exposed over
OpenAPI. Creating or updating a local tool rewrites its imports, compiles it
into a fresh module, derives its specs, and caches the live module on the
application state. The catalogue listing merges local tools with the (lazily
refreshed) remote tool servers and filters by read access for non-admins.
Valves are the Pydantic config models each module exposes.
"""

import time
from typing import Optional

from jyotigpt.config import CACHE_DIR
from jyotigpt.models.tools import (
    ToolForm,
    ToolModel,
    ToolResponse,
    ToolUserResponse,
    Tools,
)
from jyotigpt.utils.access_control import has_access
from jyotigpt.utils.plugin import load_tool_module_by_id, replace_imports
from jyotigpt.utils.tools import get_tool_specs, get_tool_servers_data


class ToolService:
    async def list_tools(self, state, user) -> list[ToolUserResponse]:
        # `state` is the ASGI application state: the config instance plus the
        # derived TOOL_SERVERS cache, refreshed once on first access.
        if not state.TOOL_SERVERS:
            state.TOOL_SERVERS = await get_tool_servers_data(
                state.config.TOOL_SERVER_CONNECTIONS
            )

        tools = Tools.get_tools()
        for server in state.TOOL_SERVERS:
            tools.append(
                ToolUserResponse(
                    **{
                        "id": f"server:{server['idx']}",
                        "user_id": f"server:{server['idx']}",
                        "name": server["openapi"]
                        .get("info", {})
                        .get("title", "Tool Server"),
                        "meta": {
                            "description": server["openapi"]
                            .get("info", {})
                            .get("description", ""),
                        },
                        "access_control": state.config.TOOL_SERVER_CONNECTIONS[
                            server["idx"]
                        ]
                        .get("config", {})
                        .get("access_control", None),
                        "updated_at": int(time.time()),
                        "created_at": int(time.time()),
                    }
                )
            )

        if user.role != "admin":
            tools = [
                tool
                for tool in tools
                if tool.user_id == user.id
                or has_access(user.id, "read", tool.access_control)
            ]

        return tools

    def list_all(self) -> list[ToolResponse]:
        return Tools.get_tools()

    def list_for_write(self, user_id: str) -> list[ToolUserResponse]:
        return Tools.get_tools_by_user_id(user_id, "write")

    def get(self, id: str) -> Optional[ToolModel]:
        return Tools.get_tool_by_id(id)

    def create(
        self, form_data: ToolForm, user_id: str, tools_cache: dict
    ) -> Optional[ToolModel]:
        form_data.content = replace_imports(form_data.content)
        tool_module, frontmatter = load_tool_module_by_id(
            form_data.id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        tools_cache[form_data.id] = tool_module

        specs = get_tool_specs(tools_cache[form_data.id])
        tool = Tools.insert_new_tool(user_id, form_data, specs)

        tool_cache_dir = CACHE_DIR / "tools" / form_data.id
        tool_cache_dir.mkdir(parents=True, exist_ok=True)

        return tool

    def update(
        self, id: str, form_data: ToolForm, tools_cache: dict
    ) -> Optional[ToolModel]:
        form_data.content = replace_imports(form_data.content)
        tool_module, frontmatter = load_tool_module_by_id(
            id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        tools_cache[id] = tool_module

        specs = get_tool_specs(tools_cache[id])
        updated = {**form_data.model_dump(exclude={"id"}), "specs": specs}
        return Tools.update_tool_by_id(id, updated)

    def delete(self, id: str, tools_cache: dict) -> bool:
        result = Tools.delete_tool_by_id(id)
        if result and id in tools_cache:
            del tools_cache[id]
        return result

    def get_valves(self, id: str) -> Optional[dict]:
        return Tools.get_tool_valves_by_id(id)

    def module_for(self, id: str, tools_cache: dict):
        if id in tools_cache:
            return tools_cache[id]
        tools_module, _ = load_tool_module_by_id(id)
        tools_cache[id] = tools_module
        return tools_module

    def valves_schema(self, module) -> Optional[dict]:
        if hasattr(module, "Valves"):
            return module.Valves.schema()
        return None

    def update_valves(self, id: str, module, values: dict) -> dict:
        values = {k: v for k, v in values.items() if v is not None}
        valves = module.Valves(**values)
        Tools.update_tool_valves_by_id(id, valves.model_dump())
        return valves.model_dump()

    def get_user_valves(self, id: str, user_id: str) -> Optional[dict]:
        return Tools.get_user_valves_by_id_and_user_id(id, user_id)

    def user_valves_schema(self, module) -> Optional[dict]:
        if hasattr(module, "UserValves"):
            return module.UserValves.schema()
        return None

    def update_user_valves(
        self, id: str, user_id: str, module, values: dict
    ) -> dict:
        values = {k: v for k, v in values.items() if v is not None}
        user_valves = module.UserValves(**values)
        Tools.update_user_valves_by_id_and_user_id(
            id, user_id, user_valves.model_dump()
        )
        return user_valves.model_dump()


tools = ToolService()
