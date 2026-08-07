"""OAuth provider integration.

Wraps Authlib's Starlette OAuth client. Provides provider registration,
login/callback flows, role and group mapping from claims, account creation
with signup gating and email-domain restrictions, profile picture fetching,
and JWT cookie issuance.
"""

import base64
import logging
import mimetypes
import sys
import uuid

import aiohttp
from authlib.integrations.starlette_client import OAuth
from authlib.oidc.core import UserInfo
from fastapi import HTTPException, status
from starlette.responses import RedirectResponse

from jyotigpt.config import (
    DEFAULT_USER_ROLE,
    ENABLE_OAUTH_GROUP_MANAGEMENT,
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    ENABLE_OAUTH_SIGNUP,
    JWT_EXPIRES_IN,
    OAUTH_ADMIN_ROLES,
    OAUTH_ALLOWED_DOMAINS,
    OAUTH_ALLOWED_ROLES,
    OAUTH_EMAIL_CLAIM,
    OAUTH_GROUPS_CLAIM,
    OAUTH_MERGE_ACCOUNTS_BY_EMAIL,
    OAUTH_PICTURE_CLAIM,
    OAUTH_PROVIDERS,
    OAUTH_ROLES_CLAIM,
    OAUTH_USERNAME_CLAIM,
    WEBHOOK_URL,
    AppConfig,
)
from jyotigpt.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from jyotigpt.env import (
    GLOBAL_LOG_LEVEL,
    JYOTIGPT_AUTH_COOKIE_SAME_SITE,
    JYOTIGPT_AUTH_COOKIE_SECURE,
    JYOTIGPT_NAME,
    SRC_LOG_LEVELS,
)
from jyotigpt.models.auths import Auths
from jyotigpt.models.groups import Groups, GroupModel, GroupUpdateForm
from jyotigpt.models.users import Users
from jyotigpt.utils.auth import create_token, get_password_hash
from jyotigpt.utils.misc import parse_duration
from jyotigpt.utils.webhook import post_webhook

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OAUTH"])

# Central config holder the manager reads from; populated once from the
# env-derived configuration values imported above.
auth_manager_config = AppConfig()
auth_manager_config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE
auth_manager_config.ENABLE_OAUTH_SIGNUP = ENABLE_OAUTH_SIGNUP
auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL = OAUTH_MERGE_ACCOUNTS_BY_EMAIL
auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT = ENABLE_OAUTH_GROUP_MANAGEMENT
auth_manager_config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
auth_manager_config.OAUTH_GROUPS_CLAIM = OAUTH_GROUPS_CLAIM
auth_manager_config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM
auth_manager_config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
auth_manager_config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
auth_manager_config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
auth_manager_config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES
auth_manager_config.OAUTH_ALLOWED_DOMAINS = OAUTH_ALLOWED_DOMAINS
auth_manager_config.WEBHOOK_URL = WEBHOOK_URL
auth_manager_config.JWT_EXPIRES_IN = JWT_EXPIRES_IN


def _get_nested_claim(user_data, claim: str):
    """Walk a dot-separated claim path through ``user_data``.

    Returns an empty dict at any missing level so the caller can check
    ``isinstance(result, list)`` safely.
    """
    value = user_data
    for part in claim.split("."):
        value = value.get(part, {})
    return value


class OAuthManager:
    """Registers OAuth providers and drives the login/callback flows."""

    def __init__(self, app):
        self.oauth = OAuth()
        self.app = app
        for _, provider_config in OAUTH_PROVIDERS.items():
            provider_config["register"](self.oauth)

    def get_client(self, provider_name):
        return self.oauth.create_client(provider_name)

    def get_user_role(self, user, user_data):
        """Determine the role to assign for ``user``/``user_data``.

        First users become admin. With role management enabled the roles
        claim is consulted against the allowed/admin role lists; otherwise
        new users get the default role and existing users keep theirs.
        """
        if user and Users.get_num_users() == 1:
            log.debug("Assigning the only user the admin role")
            return "admin"
        if not user and Users.get_num_users() == 0:
            log.debug("Assigning the first user the admin role")
            return "admin"

        if not auth_manager_config.ENABLE_OAUTH_ROLE_MANAGEMENT:
            if not user:
                return auth_manager_config.DEFAULT_USER_ROLE
            return user.role

        log.debug("Running OAUTH Role management")
        oauth_claim = auth_manager_config.OAUTH_ROLES_CLAIM
        oauth_allowed_roles = auth_manager_config.OAUTH_ALLOWED_ROLES
        oauth_admin_roles = auth_manager_config.OAUTH_ADMIN_ROLES

        role = auth_manager_config.DEFAULT_USER_ROLE

        oauth_roles = []
        if oauth_claim and oauth_allowed_roles and oauth_admin_roles:
            claim_data = _get_nested_claim(user_data, oauth_claim)
            oauth_roles = claim_data if isinstance(claim_data, list) else []

        log.debug(f"Oauth Roles claim: {oauth_claim}")
        log.debug(f"User roles from oauth: {oauth_roles}")
        log.debug(f"Accepted user roles: {oauth_allowed_roles}")
        log.debug(f"Accepted admin roles: {oauth_admin_roles}")

        if oauth_roles:
            for allowed_role in oauth_allowed_roles:
                if allowed_role in oauth_roles:
                    log.debug("Assigned user the user role")
                    role = "user"
                    break
            for admin_role in oauth_admin_roles:
                if admin_role in oauth_roles:
                    log.debug("Assigned user the admin role")
                    role = "admin"
                    break

        return role

    def update_user_groups(self, user, user_data, default_permissions):
        """Sync the user's group memberships to the provider's groups claim.

        Removes the user from local groups no longer in the claim and adds
        them to matching local groups. Groups with no explicit permissions
        fall back to the provided defaults.
        """
        log.debug("Running OAUTH Group management")
        oauth_claim = auth_manager_config.OAUTH_GROUPS_CLAIM

        user_oauth_groups = []
        if oauth_claim:
            claim_data = _get_nested_claim(user_data, oauth_claim)
            user_oauth_groups = claim_data if isinstance(claim_data, list) else []

        user_current_groups: list[GroupModel] = Groups.get_groups_by_member_id(
            user.id
        )
        all_available_groups: list[GroupModel] = Groups.get_groups()

        log.debug(f"Oauth Groups claim: {oauth_claim}")
        log.debug(f"User oauth groups: {user_oauth_groups}")
        log.debug(f"User's current groups: {[g.name for g in user_current_groups]}")
        log.debug(
            f"All groups available in JyotiGPT: {[g.name for g in all_available_groups]}"
        )

        def build_update_form(group_model: GroupModel, user_ids) -> GroupUpdateForm:
            group_permissions = group_model.permissions
            if not group_permissions:
                group_permissions = default_permissions
            return GroupUpdateForm(
                name=group_model.name,
                description=group_model.description,
                permissions=group_permissions,
                user_ids=user_ids,
            )

        # Remove memberships no longer present in the claim.
        for group_model in user_current_groups:
            if user_oauth_groups and group_model.name not in user_oauth_groups:
                log.debug(
                    f"Removing user from group {group_model.name} as it is no longer in their oauth groups"
                )
                user_ids = [i for i in group_model.user_ids if i != user.id]
                Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=build_update_form(group_model, user_ids),
                    overwrite=False,
                )

        # Add memberships newly present in the claim.
        current_names = {g.name for g in user_current_groups}
        for group_model in all_available_groups:
            if (
                user_oauth_groups
                and group_model.name in user_oauth_groups
                and group_model.name not in current_names
            ):
                log.debug(
                    f"Adding user to group {group_model.name} as it was found in their oauth groups"
                )
                user_ids = group_model.user_ids + [user.id]
                Groups.update_group_by_id(
                    id=group_model.id,
                    form_data=build_update_form(group_model, user_ids),
                    overwrite=False,
                )

    async def handle_login(self, request, provider):
        """Redirect the user to the provider's authorization endpoint."""
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        redirect_uri = OAUTH_PROVIDERS[provider].get("redirect_uri") or request.url_for(
            "oauth_callback", provider=provider
        )
        client = self.get_client(provider)
        if client is None:
            raise HTTPException(404)
        return await client.authorize_redirect(request, redirect_uri)

    async def handle_callback(self, request, provider, response):
        """Complete the OAuth exchange, create/update the user, set cookies."""
        if provider not in OAUTH_PROVIDERS:
            raise HTTPException(404)
        client = self.get_client(provider)
        try:
            token = await client.authorize_access_token(request)
        except Exception as e:
            log.warning(f"OAuth callback error: {e}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        user_data: UserInfo = token.get("userinfo")
        email_claim = auth_manager_config.OAUTH_EMAIL_CLAIM
        if not user_data or email_claim not in user_data:
            user_data = await client.userinfo(token=token)
        if not user_data:
            log.warning(f"OAuth callback failed, user data is missing: {token}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        sub = user_data.get(OAUTH_PROVIDERS[provider].get("sub_claim", "sub"))
        if not sub:
            log.warning(f"OAuth callback failed, sub is missing: {user_data}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
        provider_sub = f"{provider}@{sub}"

        email = await self._resolve_email(provider, token, user_data)
        email = email.lower()

        if (
            "*" not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
            and email.split("@")[-1] not in auth_manager_config.OAUTH_ALLOWED_DOMAINS
        ):
            log.warning(
                f"OAuth callback failed, e-mail domain is not in the list of allowed domains: {user_data}"
            )
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        user = Users.get_user_by_oauth_sub(provider_sub)

        if not user and auth_manager_config.OAUTH_MERGE_ACCOUNTS_BY_EMAIL:
            user = Users.get_user_by_email(email)
            if user:
                Users.update_user_oauth_sub_by_id(user.id, provider_sub)

        if user:
            determined_role = self.get_user_role(user, user_data)
            if user.role != determined_role:
                Users.update_user_role_by_id(user.id, determined_role)

        if not user:
            user = await self._create_user(provider, provider_sub, token, user_data, email)

        jwt_token = create_token(
            data={"id": user.id},
            expires_delta=parse_duration(auth_manager_config.JWT_EXPIRES_IN),
        )

        if (
            auth_manager_config.ENABLE_OAUTH_GROUP_MANAGEMENT
            and user.role != "admin"
        ):
            self.update_user_groups(
                user=user,
                user_data=user_data,
                default_permissions=request.app.state.config.USER_PERMISSIONS,
            )

        response.set_cookie(
            key="token",
            value=jwt_token,
            httponly=True,
            samesite=JYOTIGPT_AUTH_COOKIE_SAME_SITE,
            secure=JYOTIGPT_AUTH_COOKIE_SECURE,
        )

        if ENABLE_OAUTH_SIGNUP.value:
            oauth_id_token = token.get("id_token")
            response.set_cookie(
                key="oauth_id_token",
                value=oauth_id_token,
                httponly=True,
                samesite=JYOTIGPT_AUTH_COOKIE_SAME_SITE,
                secure=JYOTIGPT_AUTH_COOKIE_SECURE,
            )

        redirect_url = f"{request.base_url}auth#token={jwt_token}"
        return RedirectResponse(url=redirect_url, headers=response.headers)

    async def _resolve_email(self, provider, token, user_data) -> str:
        """Extract the user's email, fetching from GitHub when absent."""
        email = user_data.get(auth_manager_config.OAUTH_EMAIL_CLAIM, "")
        if email:
            return email

        if provider != "github":
            log.warning(f"OAuth callback failed, email is missing: {user_data}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

        # GitHub may omit public email; fetch it via the API with the access token.
        try:
            access_token = token.get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.github.com/user/emails", headers=headers
                ) as resp:
                    if not resp.ok:
                        log.warning("Failed to fetch GitHub email")
                        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                    emails = await resp.json()
                    primary_email = next(
                        (e["email"] for e in emails if e.get("primary")), None
                    )
                    if not primary_email:
                        log.warning("No primary email found in GitHub response")
                        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
                    return primary_email
        except Exception as e:
            log.warning(f"Error fetching GitHub email: {e}")
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    async def _fetch_profile_picture(self, token, picture_url) -> str:
        """Download a profile image and return it as a data URL, or ``/user.png``."""
        try:
            access_token = token.get("access_token")
            request_kwargs = {}
            if access_token:
                request_kwargs["headers"] = {"Authorization": f"Bearer {access_token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(picture_url, **request_kwargs) as resp:
                    if not resp.ok:
                        return "/user.png"
                    picture = await resp.read()
                    base64_picture = base64.b64encode(picture).decode("utf-8")
                    mime_type = mimetypes.guess_type(picture_url)[0]
                    if mime_type is None:
                        mime_type = "image/jpeg"
                    return f"data:{mime_type};base64,{base64_picture}"
        except Exception as e:
            log.error(f"Error downloading profile image '{picture_url}': {e}")
            return "/user.png"

    async def _create_user(self, provider, provider_sub, token, user_data, email):
        """Create a new user from OAuth data, or raise when signup is disabled."""
        if not auth_manager_config.ENABLE_OAUTH_SIGNUP:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )

        if Users.get_user_by_email(email):
            raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

        picture_url = "/user.png"
        picture_claim = auth_manager_config.OAUTH_PICTURE_CLAIM
        if picture_claim:
            candidate = user_data.get(
                picture_claim, OAUTH_PROVIDERS[provider].get("picture_url", "")
            )
            if candidate:
                picture_url = await self._fetch_profile_picture(token, candidate)
            else:
                picture_url = "/user.png"

        name = user_data.get(auth_manager_config.OAUTH_USERNAME_CLAIM)
        if not name:
            log.warning("Username claim is missing, using email as name")
            name = email

        role = self.get_user_role(None, user_data)

        user = Auths.insert_new_auth(
            email=email,
            password=get_password_hash(str(uuid.uuid4())),
            name=name,
            profile_image_url=picture_url,
            role=role,
            oauth_sub=provider_sub,
        )

        if auth_manager_config.WEBHOOK_URL:
            post_webhook(
                JYOTIGPT_NAME,
                auth_manager_config.WEBHOOK_URL,
                WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                {
                    "action": "signup",
                    "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                    "user": user.model_dump_json(exclude_none=True),
                },
            )

        return user
