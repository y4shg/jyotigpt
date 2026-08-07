"""Function plugin domain service.

Functions are user-authored Python plugins (pipes, filters, actions) stored
as source in the database. Creating or updating one rewrites its imports,
compiles it into a fresh module, records its type and docstring frontmatter,
and caches the live module on the application state so the request pipeline
can invoke it without recompiling. Valves are the Pydantic config models each
module exposes.
"""

from typing import Optional

from jyotigpt.config import CACHE_DIR
from jyotigpt.models.functions import (
    FunctionForm,
    FunctionModel,
    FunctionResponse,
    Functions,
)
from jyotigpt.utils.plugin import load_function_module_by_id, replace_imports


class FunctionService:
    def list(self) -> list[FunctionResponse]:
        return Functions.get_functions()

    def get(self, id: str) -> Optional[FunctionModel]:
        return Functions.get_function_by_id(id)

    def create(
        self, form_data: FunctionForm, user_id: str, functions_cache: dict
    ) -> Optional[FunctionModel]:
        form_data.content = replace_imports(form_data.content)
        function_module, function_type, frontmatter = load_function_module_by_id(
            form_data.id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        functions_cache[form_data.id] = function_module

        function = Functions.insert_new_function(user_id, function_type, form_data)

        function_cache_dir = CACHE_DIR / "functions" / form_data.id
        function_cache_dir.mkdir(parents=True, exist_ok=True)

        return function

    def update(
        self, id: str, form_data: FunctionForm, functions_cache: dict
    ) -> Optional[FunctionModel]:
        form_data.content = replace_imports(form_data.content)
        function_module, function_type, frontmatter = load_function_module_by_id(
            id, content=form_data.content
        )
        form_data.meta.manifest = frontmatter

        functions_cache[id] = function_module

        updated = {**form_data.model_dump(exclude={"id"}), "type": function_type}
        return Functions.update_function_by_id(id, updated)

    def set_active(self, id: str, value: bool) -> Optional[FunctionModel]:
        return Functions.update_function_by_id(id, {"is_active": value})

    def set_global(self, id: str, value: bool) -> Optional[FunctionModel]:
        return Functions.update_function_by_id(id, {"is_global": value})

    def delete(self, id: str, functions_cache: dict) -> bool:
        result = Functions.delete_function_by_id(id)
        if result and id in functions_cache:
            del functions_cache[id]
        return result

    def get_valves(self, id: str) -> Optional[dict]:
        return Functions.get_function_valves_by_id(id)

    def module_for(self, id: str, functions_cache: dict):
        if id in functions_cache:
            return functions_cache[id]
        function_module, function_type, frontmatter = load_function_module_by_id(id)
        functions_cache[id] = function_module
        return function_module

    def valves_schema(self, module) -> Optional[dict]:
        if hasattr(module, "Valves"):
            return module.Valves.schema()
        return None

    def update_valves(self, id: str, module, values: dict) -> dict:
        values = {k: v for k, v in values.items() if v is not None}
        valves = module.Valves(**values)
        Functions.update_function_valves_by_id(id, valves.model_dump())
        return valves.model_dump()

    def get_user_valves(self, id: str, user_id: str) -> Optional[dict]:
        return Functions.get_user_valves_by_id_and_user_id(id, user_id)

    def user_valves_schema(self, module) -> Optional[dict]:
        if hasattr(module, "UserValves"):
            return module.UserValves.schema()
        return None

    def update_user_valves(
        self, id: str, user_id: str, module, values: dict
    ) -> dict:
        values = {k: v for k, v in values.items() if v is not None}
        user_valves = module.UserValves(**values)
        Functions.update_user_valves_by_id_and_user_id(
            id, user_id, user_valves.model_dump()
        )
        return user_valves.model_dump()


functions = FunctionService()
