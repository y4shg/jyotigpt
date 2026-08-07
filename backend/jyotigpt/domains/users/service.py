"""User domain service.

Account records live in the ``user`` and ``auth`` tables. Users read their
own settings and info, admins manage roles and profiles. A user id of the
form ``shared-<chat_id>`` refers not to a user but to the owner of a shared
chat, resolved through the chats table before the account is looked up.
Active status is a live socket-layer signal, not a persisted field.
"""

from typing import Optional

from jyotigpt.models.auths import Auths
from jyotigpt.models.chats import Chats
from jyotigpt.models.groups import Groups
from jyotigpt.models.users import UserModel, Users
from jyotigpt.socket.main import get_active_status_by_user_id
from jyotigpt.utils.access_control import get_permissions


class UserService:
    def list(self, skip: Optional[int], limit: Optional[int]) -> list[UserModel]:
        return Users.get_users(skip, limit)

    def groups_of(self, user_id: str) -> list:
        return Groups.get_groups_by_member_id(user_id)

    def permissions_of(self, user_id: str, permissions: dict) -> dict:
        return get_permissions(user_id, permissions)

    def first_user(self) -> Optional[UserModel]:
        return Users.get_first_user()

    def update_role(self, user_id: str, role: str) -> Optional[UserModel]:
        return Users.update_user_role_by_id(user_id, role)

    def get(self, user_id: str) -> Optional[UserModel]:
        return Users.get_user_by_id(user_id)

    def get_by_email(self, email: str) -> Optional[UserModel]:
        return Users.get_user_by_email(email)

    def update_settings(self, user_id: str, settings: dict) -> Optional[UserModel]:
        return Users.update_user_settings_by_id(user_id, settings)

    def update(self, user_id: str, updates: dict) -> Optional[UserModel]:
        return Users.update_user_by_id(user_id, updates)

    def resolve_owner(self, user_id: str) -> Optional[str]:
        """Resolve a ``shared-<chat_id>`` id to its chat's owner.

        Non-shared ids pass through unchanged. A shared id whose chat no
        longer exists resolves to ``None``.
        """
        if user_id.startswith("shared-"):
            chat_id = user_id.replace("shared-", "")
            chat = Chats.get_chat_by_id(chat_id)
            if chat:
                return chat.user_id
            return None
        return user_id

    def active_status(self, user_id: str) -> Optional[bool]:
        return get_active_status_by_user_id(user_id)

    def update_password(self, user_id: str, hashed: str) -> None:
        Auths.update_user_password_by_id(user_id, hashed)

    def update_email(self, user_id: str, email: str) -> None:
        Auths.update_email_by_id(user_id, email)

    def delete_auth(self, user_id: str) -> bool:
        return Auths.delete_auth_by_id(user_id)


users = UserService()
