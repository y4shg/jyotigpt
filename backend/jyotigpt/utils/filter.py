"""Execution of filter-type function plugins.

Filters hook into the request/response lifecycle at ``inlet``, ``outlet``,
or ``stream`` stages. This module resolves which filters apply to a model,
orders them by priority, and invokes each handler with only the parameters
its signature declares.
"""

import inspect
import logging

from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.functions import Functions
from jyotigpt.utils.plugin import load_function_module_by_id

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def get_sorted_filter_ids(model: dict):
    """Return active filter function ids for ``model``, ordered by priority.

    Combines globally-enabled filters with any ``filterIds`` declared in the
    model's metadata, keeps only those currently active, and sorts ascending
    by each filter's configured ``priority`` valve (default 0).
    """

    def get_priority(function_id):
        function = Functions.get_function_by_id(function_id)
        if function is not None:
            valves = Functions.get_function_valves_by_id(function_id)
            return valves.get("priority", 0) if valves else 0
        return 0

    filter_ids = [function.id for function in Functions.get_global_filter_functions()]
    if "info" in model and "meta" in model["info"]:
        filter_ids.extend(model["info"]["meta"].get("filterIds", []))
        filter_ids = list(set(filter_ids))

    enabled_filter_ids = [
        function.id
        for function in Functions.get_functions_by_type("filter", active_only=True)
    ]

    filter_ids = [fid for fid in filter_ids if fid in enabled_filter_ids]
    filter_ids.sort(key=get_priority)
    return filter_ids


def _get_or_load_module(request, filter_id):
    """Return the cached filter module for ``filter_id``, loading it if absent."""
    if filter_id in request.app.state.FUNCTIONS:
        return request.app.state.FUNCTIONS[filter_id]

    function_module, _, _ = load_function_module_by_id(filter_id)
    request.app.state.FUNCTIONS[filter_id] = function_module
    return function_module


def _apply_valves(function_module, filter_id):
    """Instantiate the module's ``Valves`` from stored config, if defined."""
    if hasattr(function_module, "valves") and hasattr(function_module, "Valves"):
        valves = Functions.get_function_valves_by_id(filter_id)
        function_module.valves = function_module.Valves(**(valves if valves else {}))


def _build_handler_params(handler, filter_type, form_data, extra_params, filter_id):
    """Select the handler kwargs the handler's signature actually accepts."""
    sig = inspect.signature(handler)

    if filter_type == "stream":
        params = {"event": form_data}
    else:
        params = {"body": form_data}

    candidate = {**extra_params, "__id__": filter_id}
    params.update({k: v for k, v in candidate.items() if k in sig.parameters})
    return params, sig


async def process_filter_functions(
    request, filter_functions, filter_type, form_data, extra_params
):
    """Run each filter's ``filter_type`` handler in sequence over ``form_data``.

    Each handler receives the (possibly transformed) form data plus any
    matching extra params and user valves. Async handlers are awaited. If any
    filter declared a ``file_handler``, attached files are stripped from the
    inlet result afterward. Returns ``(form_data, {})``.
    """
    skip_files = None

    for function in filter_functions:
        if not function:
            continue
        filter_id = function.id

        function_module = _get_or_load_module(request, filter_id)

        handler = getattr(function_module, filter_type, None)
        if not handler:
            continue

        if filter_type == "inlet" and hasattr(function_module, "file_handler"):
            skip_files = function_module.file_handler

        _apply_valves(function_module, filter_id)

        try:
            params, sig = _build_handler_params(
                handler, filter_type, form_data, extra_params, filter_id
            )

            if "__user__" in sig.parameters and hasattr(
                function_module, "UserValves"
            ):
                try:
                    params["__user__"]["valves"] = function_module.UserValves(
                        **Functions.get_user_valves_by_id_and_user_id(
                            filter_id, params["__user__"]["id"]
                        )
                    )
                except Exception as e:
                    log.exception(f"Failed to get user values: {e}")

            if inspect.iscoroutinefunction(handler):
                form_data = await handler(**params)
            else:
                form_data = handler(**params)
        except Exception as e:
            log.debug(f"Error in {filter_type} handler {filter_id}: {e}")
            raise e

    if skip_files and "files" in form_data.get("metadata", {}):
        del form_data["files"]
        del form_data["metadata"]["files"]

    return form_data, {}
