"""Folder domain service.

Folders are user-scoped groupings for chats, nestable through a parent id.
Responses are enriched with the chats each folder contains. Sibling-name
collision checks and cascade deletion live at the data layer; this service
just orchestrates them.
"""

from typing import Optional

from jyotigpt.models.chats import Chats
from jyotigpt.models.folders import FolderModel, Folders


class FolderService:
    def list_with_chat_items(self, user_id: str) -> list[dict]:
        return [
            {
                **folder.model_dump(),
                "items": {
                    "chats": [
                        {"title": chat.title, "id": chat.id}
                        for chat in Chats.get_chats_by_folder_id_and_user_id(
                            folder.id, user_id
                        )
                    ]
                },
            }
            for folder in Folders.get_folders_by_user_id(user_id)
        ]

    def get(self, id: str, user_id: str) -> Optional[FolderModel]:
        return Folders.get_folder_by_id_and_user_id(id, user_id)

    def create(self, user_id: str, name: str) -> FolderModel:
        return Folders.insert_new_folder(user_id, name)

    def has_sibling_named(
        self, parent_id: Optional[str], user_id: str, name: str
    ) -> bool:
        return (
            Folders.get_folder_by_parent_id_and_user_id_and_name(
                parent_id, user_id, name
            )
            is not None
        )

    def rename(self, id: str, user_id: str, name: str) -> Optional[FolderModel]:
        return Folders.update_folder_name_by_id_and_user_id(id, user_id, name)

    def move(
        self, id: str, user_id: str, parent_id: Optional[str]
    ) -> Optional[FolderModel]:
        return Folders.update_folder_parent_id_by_id_and_user_id(
            id, user_id, parent_id
        )

    def set_expanded(
        self, id: str, user_id: str, is_expanded: bool
    ) -> Optional[FolderModel]:
        return Folders.update_folder_is_expanded_by_id_and_user_id(
            id, user_id, is_expanded
        )

    def delete(self, id: str, user_id: str) -> bool:
        return Folders.delete_folder_by_id_and_user_id(id, user_id)


folders = FolderService()
