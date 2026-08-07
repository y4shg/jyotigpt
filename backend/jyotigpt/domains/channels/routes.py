"""Channel HTTP routes.

Channels are group chats. Admins create, edit, and delete channels; anyone
can read a channel's messages (and post to them) if they have read access
under its access control. Every message write (post, edit, reaction,
delete) fans out a ``channel-events`` socket event to the ``channel:<id>``
room; posts also schedule a background webhook notification for channel
members who are not currently present in the room.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from jyotigpt.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from jyotigpt.constants import ERROR_MESSAGES
from jyotigpt.env import SRC_LOG_LEVELS
from jyotigpt.models.channels import ChannelForm, ChannelModel
from jyotigpt.models.messages import MessageForm, MessageModel, MessageResponse
from jyotigpt.models.users import UserNameResponse, Users
from jyotigpt.socket.main import get_user_ids_from_room, sio
from jyotigpt.utils.access_control import get_users_with_access, has_access
from jyotigpt.utils.auth import get_admin_user, get_verified_user
from jyotigpt.utils.webhook import post_webhook

from .service import channels

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


class MessageUserResponse(MessageResponse):
    user: UserNameResponse


class ReactionForm(BaseModel):
    name: str


def _get_channel_or_404(channel_id: str) -> ChannelModel:
    """Fetch a channel or raise the canonical 404."""
    channel = channels.get(channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )
    return channel


def _authorize_channel_read(user, channel: ChannelModel) -> None:
    """Admins bypass channel access control; everyone else must have read access."""
    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )


def _require_message_in_channel(channel_id: str, message_id: str) -> MessageModel:
    """Fetch a message that belongs to the given channel, or raise."""
    message = channels.get_message(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )
    if message.channel_id != channel_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
    return message


def _enrich(message: MessageModel) -> MessageUserResponse:
    """Build the wire response for a channel message."""
    user = Users.get_user_by_id(message.user_id)
    return MessageUserResponse(
        **{
            **message.model_dump(),
            "user": UserNameResponse(**user.model_dump()),
        }
    )


############################
# GetChatList
############################


@router.get("/", response_model=list[ChannelModel])
async def get_channels(user=Depends(get_verified_user)):
    if user.role == "admin":
        return channels.list_all()
    return channels.list_for_user(user.id)


############################
# CreateNewChannel
############################


@router.post("/create", response_model=Optional[ChannelModel])
async def create_new_channel(form_data: ChannelForm, user=Depends(get_admin_user)):
    try:
        channel = channels.create(form_data, user.id)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelById
############################


@router.get("/{id}", response_model=Optional[ChannelModel])
async def get_channel_by_id(id: str, user=Depends(get_verified_user)):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    return ChannelModel(**channel.model_dump())


############################
# UpdateChannelById
############################


@router.post("/{id}/update", response_model=Optional[ChannelModel])
async def update_channel_by_id(
    id: str, form_data: ChannelForm, user=Depends(get_admin_user)
):
    _get_channel_or_404(id)

    try:
        channel = channels.update(id, form_data)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChannelById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_channel_by_id(id: str, user=Depends(get_admin_user)):
    _get_channel_or_404(id)

    try:
        channels.delete(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelMessages
############################


@router.get("/{id}/messages", response_model=list[MessageUserResponse])
async def get_channel_messages(
    id: str, skip: int = 0, limit: int = 50, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)

    users = {}

    messages = []
    for message in channels.get_messages(id, skip, limit):
        if message.user_id not in users:
            users[message.user_id] = Users.get_user_by_id(message.user_id)

        replies = channels.get_replies(message.id)
        latest_reply_at = replies[0].created_at if replies else None

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": len(replies),
                    "latest_reply_at": latest_reply_at,
                    "reactions": channels.get_reactions(message.id),
                    "user": UserNameResponse(**users[message.user_id].model_dump()),
                }
            )
        )

    return messages


############################
# PostNewMessage
############################


def send_notification(name, jyotigpt_url, channel, message, active_user_ids):
    users = get_users_with_access("read", channel.access_control)

    for user in users:
        if user.id in active_user_ids:
            continue
        else:
            if user.settings:
                webhook_url = user.settings.ui.get("notifications", {}).get(
                    "webhook_url", None
                )

                if webhook_url:
                    post_webhook(
                        name,
                        webhook_url,
                        f"#{channel.name} - {jyotigpt_url}/channels/{channel.id}\n\n{message.content}",
                        {
                            "action": "channel",
                            "message": message.content,
                            "title": channel.name,
                            "url": f"{jyotigpt_url}/channels/{channel.id}",
                        },
                    )


@router.post("/{id}/messages/post", response_model=Optional[MessageModel])
async def post_new_message(
    request: Request,
    id: str,
    form_data: MessageForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)

    try:
        message = channels.create_message(form_data, channel.id, user.id)

        if message:
            event_data = {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message",
                    "data": MessageUserResponse(
                        **{
                            **message.model_dump(),
                            "reply_count": 0,
                            "latest_reply_at": None,
                            "reactions": channels.get_reactions(message.id),
                            "user": UserNameResponse(**user.model_dump()),
                        }
                    ).model_dump(),
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            }

            await sio.emit(
                "channel-events",
                event_data,
                to=f"channel:{channel.id}",
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = channels.get_message(message.parent_id)

                if parent_message:
                    await sio.emit(
                        "channel-events",
                        {
                            "channel_id": channel.id,
                            "message_id": parent_message.id,
                            "data": {
                                "type": "message:reply",
                                "data": MessageUserResponse(
                                    **{
                                        **parent_message.model_dump(),
                                        "user": UserNameResponse(
                                            **Users.get_user_by_id(
                                                parent_message.user_id
                                            ).model_dump()
                                        ),
                                    }
                                ).model_dump(),
                            },
                            "user": UserNameResponse(**user.model_dump()).model_dump(),
                            "channel": channel.model_dump(),
                        },
                        to=f"channel:{channel.id}",
                    )

            active_user_ids = get_user_ids_from_room(f"channel:{channel.id}")

            background_tasks.add_task(
                send_notification,
                request.app.state.JYOTIGPT_NAME,
                request.app.state.config.jyotigpt_url,
                channel,
                message,
                active_user_ids,
            )

        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelMessage
############################


@router.get("/{id}/messages/{message_id}", response_model=Optional[MessageUserResponse])
async def get_channel_message(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    message = _require_message_in_channel(id, message_id)
    return _enrich(message)


############################
# GetChannelThreadMessages
############################


@router.get(
    "/{id}/messages/{message_id}/thread", response_model=list[MessageUserResponse]
)
async def get_channel_thread_messages(
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)

    users = {}

    messages = []
    for message in channels.get_thread(id, message_id, skip, limit):
        if message.user_id not in users:
            users[message.user_id] = Users.get_user_by_id(message.user_id)

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": 0,
                    "latest_reply_at": None,
                    "reactions": channels.get_reactions(message.id),
                    "user": UserNameResponse(**users[message.user_id].model_dump()),
                }
            )
        )

    return messages


############################
# UpdateMessageById
############################


@router.post(
    "/{id}/messages/{message_id}/update", response_model=Optional[MessageModel]
)
async def update_message_by_id(
    id: str, message_id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    _require_message_in_channel(id, message_id)

    try:
        channels.update_message(message_id, form_data)
        message = channels.get_message(message_id)

        if message:
            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "data": {
                        "type": "message:update",
                        "data": MessageUserResponse(
                            **{
                                **message.model_dump(),
                                "user": UserNameResponse(**user.model_dump()).model_dump(),
                            }
                        ).model_dump(),
                    },
                    "user": UserNameResponse(**user.model_dump()).model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )

        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# AddReactionToMessage
############################


@router.post("/{id}/messages/{message_id}/reactions/add", response_model=bool)
async def add_reaction_to_message(
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    message = _require_message_in_channel(id, message_id)

    try:
        channels.add_reaction(message_id, user.id, form_data.name)
        message = channels.get_message(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:add",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(
                            **Users.get_user_by_id(message.user_id).model_dump()
                        ).model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# RemoveReactionById
############################


@router.post("/{id}/messages/{message_id}/reactions/remove", response_model=bool)
async def remove_reaction_by_id_and_user_id_and_name(
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    message = _require_message_in_channel(id, message_id)

    try:
        channels.remove_reaction(message_id, user.id, form_data.name)
        message = channels.get_message(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:remove",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(
                            **Users.get_user_by_id(message.user_id).model_dump()
                        ).model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteMessageById
############################


@router.delete("/{id}/messages/{message_id}/delete", response_model=bool)
async def delete_message_by_id(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = _get_channel_or_404(id)
    _authorize_channel_read(user, channel)
    message = _require_message_in_channel(id, message_id)

    try:
        channels.delete_message(message_id)
        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:delete",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        if message.parent_id:
            # If this message is a reply, emit to the parent message as well
            parent_message = channels.get_message(message.parent_id)

            if parent_message:
                await sio.emit(
                    "channel-events",
                    {
                        "channel_id": channel.id,
                        "message_id": parent_message.id,
                        "data": {
                            "type": "message:reply",
                            "data": MessageUserResponse(
                                **{
                                    **parent_message.model_dump(),
                                    "user": UserNameResponse(
                                        **Users.get_user_by_id(
                                            parent_message.user_id
                                        ).model_dump()
                                    ),
                                }
                            ).model_dump(),
                        },
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                        "channel": channel.model_dump(),
                    },
                    to=f"channel:{channel.id}",
                )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
