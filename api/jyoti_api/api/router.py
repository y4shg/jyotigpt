"""Aggregate router wiring every endpoint group under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from jyoti_api.api import (
    auth,
    capabilities,
    chat,
    collections,
    conversations,
    documents,
    evaluations,
    flows,
    folders,
    images,
    models,
    notes,
    playground,
    plugins,
    preferences,
    presets,
    rooms,
    search,
    settings,
    stt,
    tts,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(settings.router)
api_router.include_router(preferences.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(folders.router)
api_router.include_router(presets.router)
api_router.include_router(capabilities.router)
api_router.include_router(plugins.router)
api_router.include_router(documents.router)
api_router.include_router(collections.router)
api_router.include_router(models.router)
api_router.include_router(images.router)
api_router.include_router(flows.router)
api_router.include_router(evaluations.router)
api_router.include_router(rooms.router)
api_router.include_router(notes.router)
api_router.include_router(playground.router)
api_router.include_router(stt.router)
api_router.include_router(tts.router)
api_router.include_router(search.router)
