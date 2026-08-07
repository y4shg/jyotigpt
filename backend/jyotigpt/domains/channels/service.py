"""Channel domain service.

Channels provide group chat capabilities. Like tools and folders, they use
access control to determine visibility, and messages are tied to a channel
and a user. Creating or updating a message emits socket.io events and sends
webhooks for background notification.
"""

from typing import Optional

from jyotigpt.models.channels import ChannelForm, ChannelModel, Channels
from jyotigpt.models.messages import MessageForm, MessageModel, Messages


class ChannelService:
    def list_all(self) -> list[ChannelModel]:
        return Channels.get_channels()

    def list_for_user(self, user_id: str) -> list[ChannelModel]:
        return Channels.get_channels_by_user_id(user_id)

    def get(self, id: str) -> Optional[ChannelModel]:
        return Channels.get_channel_by_id(id)

    def create(self, form_data: ChannelForm, user_id: str) -> ChannelModel:
        return Channels.insert_new_channel(None, form_data, user_id)

    def update(self, id: str, form_data: ChannelForm) -> ChannelModel:
        return Channels.update_channel_by_id(id, form_data)

    def delete(self, id: str) -> bool:
        return Channels.delete_channel_by_id(id)

    def get_messages(self, channel_id: str, skip: int, limit: int) -> list[MessageModel]:
        return Messages.get_messages_by_channel_id(channel_id, skip, limit)

    def get_thread(
        self, channel_id: str, message_id: str, skip: int, limit: int
    ) -> list[MessageModel]:
        return Messages.get_messages_by_parent_id(channel_id, message_id, skip, limit)

    def get_message(self, message_id: str) -> Optional[MessageModel]:
        return Messages.get_message_by_id(message_id)

    def create_message(
        self, form_data: MessageForm, channel_id: str, user_id: str
    ) -> Optional[MessageModel]:
        return Messages.insert_new_message(form_data, channel_id, user_id)

    def update_message(
        self, message_id: str, form_data: MessageForm
    ) -> Optional[MessageModel]:
        return Messages.update_message_by_id(message_id, form_data)

    def delete_message(self, message_id: str) -> bool:
        return Messages.delete_message_by_id(message_id)

    def get_replies(self, message_id: str) -> list[MessageModel]:
        return Messages.get_replies_by_message_id(message_id)

    def get_reactions(self, message_id: str) -> list[str]:
        return Messages.get_reactions_by_message_id(message_id)

    def add_reaction(self, message_id: str, user_id: str, name: str) -> bool:
        return Messages.add_reaction_to_message(message_id, user_id, name)

    def remove_reaction(self, message_id: str, user_id: str, name: str) -> bool:
        return Messages.remove_reaction_by_id_and_user_id_and_name(
            message_id, user_id, name
        )


channels = ChannelService()
