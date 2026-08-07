"""Chat domain service.

Chats are the per-user conversation records; a single ``chat`` table row
holds the whole conversation as a nested JSON document, so most updates
re-read the row after writing. Tags are lightweight labels shared across a
user's chats, and folders group chats into a tree — both are kept in sync
by the routes whenever a chat's tags or folder change.
"""

from typing import Optional

from jyotigpt.models.chats import (
    ChatForm,
    ChatImportForm,
    ChatModel,
    Chats,
    ChatTitleIdResponse,
)
from jyotigpt.models.folders import FolderModel, Folders
from jyotigpt.models.tags import TagModel, Tags


class ChatService:
    # -- chat list / browse ------------------------------------------------

    def list_title_ids(
        self, user_id: str, skip: Optional[int] = None, limit: Optional[int] = None
    ) -> list[ChatTitleIdResponse]:
        if skip is None:
            return Chats.get_chat_title_id_list_by_user_id(user_id)
        return Chats.get_chat_title_id_list_by_user_id(
            user_id, skip=skip, limit=limit
        )

    def list_by_user(
        self, user_id: str, include_archived: bool, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        return Chats.get_chat_list_by_user_id(
            user_id, include_archived=include_archived, skip=skip, limit=limit
        )

    def search(
        self, user_id: str, text: str, skip: int = 0, limit: int = 50
    ) -> list[ChatModel]:
        return Chats.get_chats_by_user_id_and_search_text(
            user_id, text, skip=skip, limit=limit
        )

    def by_folder(
        self, folder_ids: list[str], user_id: str
    ) -> list[ChatModel]:
        return Chats.get_chats_by_folder_ids_and_user_id(folder_ids, user_id)

    def children_folders(self, folder_id: str, user_id: str) -> list[FolderModel]:
        return Folders.get_children_folders_by_id_and_user_id(folder_id, user_id)

    def pinned(self, user_id: str) -> list[ChatModel]:
        return Chats.get_pinned_chats_by_user_id(user_id)

    def all(self, user_id: str) -> list[ChatModel]:
        return Chats.get_chats_by_user_id(user_id)

    def archived(self, user_id: str) -> list[ChatModel]:
        return Chats.get_archived_chats_by_user_id(user_id)

    def archived_list(
        self, user_id: str, skip: int = 0, limit: int = 50
    ) -> list[ChatTitleIdResponse]:
        return Chats.get_archived_chat_list_by_user_id(user_id, skip, limit)

    def all_in_db(self) -> list[ChatModel]:
        return Chats.get_chats()

    def tags_of(self, user_id: str) -> list[TagModel]:
        return Tags.get_tags_by_user_id(user_id)

    # -- create / import ----------------------------------------------------

    def create(self, user_id: str, form_data: ChatForm) -> Optional[ChatModel]:
        return Chats.insert_new_chat(user_id, form_data)

    def import_chat(
        self, user_id: str, form_data: ChatImportForm
    ) -> Optional[ChatModel]:
        return Chats.import_chat(user_id, form_data)

    def clone(self, user_id: str, chat: dict) -> Optional[ChatModel]:
        return Chats.insert_new_chat(user_id, ChatForm(**{"chat": chat}))

    # -- single-chat lookups -----------------------------------------------

    def get(self, id: str) -> Optional[ChatModel]:
        return Chats.get_chat_by_id(id)

    def get_by_share_id(self, id: str) -> Optional[ChatModel]:
        return Chats.get_chat_by_share_id(id)

    def get_by_user(self, id: str, user_id: str) -> Optional[ChatModel]:
        return Chats.get_chat_by_id_and_user_id(id, user_id)

    # -- mutations ----------------------------------------------------------

    def update(self, id: str, chat: dict) -> Optional[ChatModel]:
        return Chats.update_chat_by_id(id, chat)

    def upsert_message(
        self, id: str, message_id: str, content: str
    ) -> Optional[ChatModel]:
        return Chats.upsert_message_to_chat_by_id_and_message_id(
            id, message_id, {"content": content}
        )

    def delete(self, id: str) -> bool:
        return Chats.delete_chat_by_id(id)

    def delete_by_user(self, id: str, user_id: str) -> bool:
        return Chats.delete_chat_by_id_and_user_id(id, user_id)

    def delete_all(self, user_id: str) -> bool:
        return Chats.delete_chats_by_user_id(user_id)

    def archive_all(self, user_id: str) -> bool:
        return Chats.archive_all_chats_by_user_id(user_id)

    def toggle_pinned(self, id: str) -> Optional[ChatModel]:
        return Chats.toggle_chat_pinned_by_id(id)

    def toggle_archive(self, id: str) -> Optional[ChatModel]:
        return Chats.toggle_chat_archive_by_id(id)

    def update_folder(
        self, id: str, user_id: str, folder_id: Optional[str]
    ) -> Optional[ChatModel]:
        return Chats.update_chat_folder_id_by_id_and_user_id(id, user_id, folder_id)

    # -- sharing ------------------------------------------------------------

    def insert_share(self, id: str) -> Optional[ChatModel]:
        return Chats.insert_shared_chat_by_chat_id(id)

    def update_share(self, id: str) -> Optional[ChatModel]:
        return Chats.update_shared_chat_by_chat_id(id)

    def delete_share(self, id: str) -> bool:
        return Chats.delete_shared_chat_by_chat_id(id)

    def clear_share_id(self, id: str) -> Optional[ChatModel]:
        return Chats.update_chat_share_id_by_id(id, None)

    # -- tags ---------------------------------------------------------------

    def chats_by_tag(
        self, user_id: str, name: str, skip: int = 0, limit: int = 50
    ) -> list[ChatTitleIdResponse]:
        return Chats.get_chat_list_by_user_id_and_tag_name(user_id, name, skip, limit)

    def add_tag(self, id: str, user_id: str, name: str) -> None:
        Chats.add_chat_tag_by_id_and_user_id_and_tag_name(id, user_id, name)

    def delete_tag(self, id: str, user_id: str, name: str) -> None:
        Chats.delete_tag_by_id_and_user_id_and_tag_name(id, user_id, name)

    def delete_all_tags(self, id: str, user_id: str) -> bool:
        return Chats.delete_all_tags_by_id_and_user_id(id, user_id)

    def count_by_tag(self, tag_name: str, user_id: str) -> int:
        return Chats.count_chats_by_tag_name_and_user_id(tag_name, user_id)

    def tags_by_ids(self, tag_ids: list, user_id: str) -> list[TagModel]:
        return Tags.get_tags_by_ids_and_user_id(tag_ids, user_id)

    def tag_by_name_and_user(self, name: str, user_id: str) -> Optional[TagModel]:
        return Tags.get_tag_by_name_and_user_id(name, user_id)

    def insert_tag(self, name: str, user_id: str) -> Optional[TagModel]:
        return Tags.insert_new_tag(name, user_id)

    def delete_tag_by_name_and_user(self, name: str, user_id: str) -> bool:
        return Tags.delete_tag_by_name_and_user_id(name, user_id)

    # -- tag lifecycle helpers ----------------------------------------------

    def ensure_import_tags(self, user_id: str, tag_ids: list) -> None:
        """Recreate the standalone tag rows a freshly imported chat references."""
        for tag_id in tag_ids:
            tag_id = tag_id.replace(" ", "_").lower()
            tag_name = " ".join([word.capitalize() for word in tag_id.split("_")])
            if (
                tag_id != "none"
                and self.tag_by_name_and_user(tag_name, user_id) is None
            ):
                self.insert_tag(tag_name, user_id)

    def drop_tag_if_last_use(self, tag_name: str, user_id: str) -> None:
        """Remove the tag row once no chat references it anymore."""
        if self.count_by_tag(tag_name, user_id) == 0:
            self.delete_tag_by_name_and_user(tag_name, user_id)


chats = ChatService()
