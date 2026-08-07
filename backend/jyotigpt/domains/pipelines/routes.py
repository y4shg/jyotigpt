"""Admin HTTP surface for the pipelines proxy.

Relays to the configured OpenAI-compatible providers: pipeline list,
upload/add/delete of pipelines, and read/update of per-pipeline valves.
All routes require an admin user.
"""

import logging
import shutil

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from typing import Optional

from jyotigpt.config import CACHE_DIR
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.utils.auth import get_admin_user

from jyotigpt.domains.openai.service import get_all_models_responses
from jyotigpt.domains.pipelines.service import pipelines_proxy

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


@router.get("/list")
async def get_pipelines_list(request: Request, user=Depends(get_admin_user)):
    """Providers whose instance is itself a pipelines server."""
    responses = await get_all_models_responses(request, user)
    log.debug(f"get_pipelines_list: get_openai_models_responses returned {responses}")

    url_idxs = [
        idx
        for idx, response in enumerate(responses)
        if response is not None and "pipelines" in response
    ]

    return {
        "data": [
            {
                "url": request.app.state.config.OPENAI_API_BASE_URLS[url_idx],
                "idx": url_idx,
            }
            for url_idx in url_idxs
        ]
    }


@router.post("/upload")
async def upload_pipeline(
    request: Request,
    urlIdx: int = Form(...),
    file: UploadFile = File(...),
    user=Depends(get_admin_user),
):
    log.info(f"upload_pipeline: urlIdx={urlIdx}, filename={file.filename}")
    if not (file.filename and file.filename.endswith(".py")):
        raise HTTPException(
            status_code=400,
            detail="Only Python (.py) files are allowed.",
        )

    upload_folder = CACHE_DIR / "pipelines"
    upload_folder.mkdir(parents=True, exist_ok=True)
    file_path = upload_folder / file.filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with open(file_path, "rb") as f:
            return pipelines_proxy(
                request, urlIdx, "POST", "pipelines/upload", files={"file": f}
            )
    finally:
        # The upload is relayed verbatim; the local copy is throwaway
        if file_path.exists():
            file_path.unlink()


class AddPipelineForm(BaseModel):
    url: str
    urlIdx: int


@router.post("/add")
async def add_pipeline(
    request: Request, form_data: AddPipelineForm, user=Depends(get_admin_user)
):
    return pipelines_proxy(
        request, form_data.urlIdx, "POST", "pipelines/add", json_body={"url": form_data.url}
    )


class DeletePipelineForm(BaseModel):
    id: str
    urlIdx: int


@router.delete("/delete")
async def delete_pipeline(
    request: Request, form_data: DeletePipelineForm, user=Depends(get_admin_user)
):
    return pipelines_proxy(
        request, form_data.urlIdx, "DELETE", "pipelines/delete", json_body={"id": form_data.id}
    )


@router.get("/")
async def get_pipelines(
    request: Request, urlIdx: Optional[int] = None, user=Depends(get_admin_user)
):
    return pipelines_proxy(request, urlIdx, "GET", "pipelines")


@router.get("/{pipeline_id}/valves")
async def get_pipeline_valves(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    return pipelines_proxy(request, urlIdx, "GET", f"{pipeline_id}/valves")


@router.get("/{pipeline_id}/valves/spec")
async def get_pipeline_valves_spec(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    user=Depends(get_admin_user),
):
    return pipelines_proxy(request, urlIdx, "GET", f"{pipeline_id}/valves/spec")


@router.post("/{pipeline_id}/valves/update")
async def update_pipeline_valves(
    request: Request,
    urlIdx: Optional[int],
    pipeline_id: str,
    form_data: dict,
    user=Depends(get_admin_user),
):
    return pipelines_proxy(
        request, urlIdx, "POST", f"{pipeline_id}/valves/update", json_body={**form_data}
    )
