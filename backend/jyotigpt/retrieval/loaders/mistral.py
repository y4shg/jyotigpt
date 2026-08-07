"""Mistral OCR document loader.

Processes a local PDF through the Mistral OCR API: upload the file, ask
for a short-lived signed URL, run OCR on it, and delete the file from
Mistral storage again. Each page becomes a ``Document`` carrying
0-based ``page``, 1-based ``page_label``, and ``total_pages`` metadata.
"""

import logging
import os
import sys
from typing import Any, Dict, List

import requests

from langchain_core.documents import Document
from jyotigpt.env import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class MistralLoader:
    """Loads documents by processing them through the Mistral OCR API."""

    BASE_API_URL = "https://api.mistral.ai/v1"

    def __init__(self, api_key: str, file_path: str):
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        self.api_key = api_key
        self.file_path = file_path
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    # --- low-level request helpers ----------------------------------------

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Turn a response into JSON, logging and re-raising on failure."""
        try:
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            log.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            raise
        except requests.exceptions.RequestException as req_err:
            log.error(f"Request exception occurred: {req_err}")
            raise
        except ValueError as json_err:
            log.error(f"JSON decode error: {json_err} - Response: {response.text}")
            raise

    def _upload_file(self) -> str:
        """Upload the file with purpose ``ocr`` and return its file ID."""
        log.info("Uploading file to Mistral API")
        url = f"{self.BASE_API_URL}/files"
        file_name = os.path.basename(self.file_path)

        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (file_name, f, "application/pdf")}
                data = {"purpose": "ocr"}
                upload_headers = self.headers.copy()
                response = requests.post(
                    url, headers=upload_headers, files=files, data=data
                )

            response_data = self._handle_response(response)
            file_id = response_data.get("id")
            if not file_id:
                raise ValueError("File ID not found in upload response.")
            log.info(f"File uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"Failed to upload file: {e}")
            raise

    def _get_signed_url(self, file_id: str) -> str:
        """Request a 1-hour signed URL for an uploaded file."""
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
        params = {"expiry": 1}
        signed_url_headers = {**self.headers, "Accept": "application/json"}

        try:
            response = requests.get(url, headers=signed_url_headers, params=params)
            response_data = self._handle_response(response)
            signed_url = response_data.get("url")
            if not signed_url:
                raise ValueError("Signed URL not found in response.")
            log.info("Signed URL received.")
            return signed_url
        except Exception as e:
            log.error(f"Failed to get signed URL: {e}")
            raise

    def _process_ocr(self, signed_url: str) -> Dict[str, Any]:
        """Run OCR on the signed URL with the current OCR model."""
        log.info("Processing OCR via Mistral API")
        url = f"{self.BASE_API_URL}/ocr"
        ocr_headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": signed_url,
            },
            "include_image_base64": False,
        }

        try:
            response = requests.post(url, headers=ocr_headers, json=payload)
            ocr_response = self._handle_response(response)
            log.info("OCR processing done.")
            log.debug("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    def _delete_file(self, file_id: str) -> None:
        """Remove the uploaded file from Mistral storage."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"

        try:
            response = requests.delete(url, headers=self.headers)
            delete_response = self._handle_response(response)
            log.info(f"File deleted successfully: {delete_response}")
        except Exception as e:
            log.error(f"Failed to delete file ID {file_id}: {e}")

    # --- pipeline ---------------------------------------------------------

    def load(self) -> List[Document]:
        """Upload → signed URL → OCR → cleanup; one Document per page."""
        file_id = None
        try:
            file_id = self._upload_file()
            signed_url = self._get_signed_url(file_id)
            ocr_response = self._process_ocr(signed_url)

            pages_data = ocr_response.get("pages")
            if not pages_data:
                log.warning("No pages found in OCR response.")
                return [Document(page_content="No text content found", metadata={})]

            documents = []
            total_pages = len(pages_data)
            for page_data in pages_data:
                page_content = page_data.get("markdown")
                page_index = page_data.get("index")  # 0-based from the API

                if page_content is not None and page_index is not None:
                    documents.append(
                        Document(
                            page_content=page_content,
                            metadata={
                                "page": page_index,
                                "page_label": page_index + 1,
                                "total_pages": total_pages,
                            },
                        )
                    )
                else:
                    log.warning(
                        f"Skipping page due to missing 'markdown' or 'index'. Data: {page_data}"
                    )

            if not documents:
                log.warning(
                    "OCR response contained pages, but none had valid content/index."
                )
                return [
                    Document(
                        page_content="No text content found in valid pages", metadata={}
                    )
                ]

            return documents

        except Exception as e:
            log.error(f"An error occurred during the loading process: {e}")
            return [Document(page_content=f"Error during processing: {e}", metadata={})]
        finally:
            if file_id:
                try:
                    self._delete_file(file_id)
                except Exception as del_e:
                    log.error(
                        f"Cleanup error: Could not delete file ID {file_id}. Reason: {del_e}"
                    )
