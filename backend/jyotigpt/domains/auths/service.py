"""Auth domain service.

Owns the identity flows behind the auth HTTP surface: password and
trusted-header sign-in, first-user sign-up, LDAP binds, and admin user
creation. Every successful flow ends in the same token session — a JWT
stored both in the payload and in the ``token`` cookie the frontend
relies on — with the user's permission set attached.
"""

import datetime
import logging
import time
import uuid

from typing import Optional

from fastapi import HTTPException, Request, Response, status

from jyotigpt.config import ENABLE_LDAP
from jyotigpt.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from jyotigpt.env import (
    JYOTIGPT_AUTH,
    JYOTIGPT_AUTH_COOKIE_SAME_SITE,
    JYOTIGPT_AUTH_COOKIE_SECURE,
    JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER,
    JYOTIGPT_AUTH_TRUSTED_NAME_HEADER,
)
from jyotigpt.models.auths import Auths, SigninForm, SignupForm
from jyotigpt.models.users import Users
from jyotigpt.utils.access_control import get_permissions
from jyotigpt.utils.auth import create_token, get_password_hash
from jyotigpt.utils.misc import parse_duration, validate_email_format
from jyotigpt.utils.webhook import post_webhook

if ENABLE_LDAP.value:
    from ssl import CERT_REQUIRED, PROTOCOL_TLS
    from ldap3 import NONE, Connection, Server, Tls
    from ldap3.utils.conv import escape_filter_chars

log = logging.getLogger(__name__)


class AuthService:
    # -- session helpers -------------------------------------------------

    @staticmethod
    def _session_payload(
        user,
        token: str,
        *,
        expires_at: Optional[int] = None,
        permissions: Optional[dict] = None,
    ) -> dict:
        """The session JSON every auth endpoint returns.

        Key order is significant to the shared response shape: the optional
        ``expires_at`` and ``permissions`` fields are only present on the
        flows that set them (LDAP and admin-add omit them).
        """
        payload = {"token": token, "token_type": "Bearer"}
        if expires_at is not None:
            payload["expires_at"] = expires_at
        payload.update(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "profile_image_url": user.profile_image_url,
            }
        )
        if permissions is not None:
            payload["permissions"] = permissions
        return payload

    @staticmethod
    def _set_token_cookie(
        response: Response,
        token: str,
        *,
        expires_at: Optional[int] = None,
        full_cookie: bool = True,
    ) -> None:
        """Persist the session token as the ``token`` cookie.

        ``full_cookie`` reproduces the secure session cookie used by the
        main flows (expiry plus same-site/secure flags); the LDAP flow
        historically sets a bare httponly cookie, which the flag preserves.
        """
        datetime_expires_at = (
            datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc)
            if expires_at
            else None
        )

        cookie_kwargs = {"httponly": True}
        if datetime_expires_at is not None:
            cookie_kwargs["expires"] = datetime_expires_at
        if full_cookie:
            cookie_kwargs["samesite"] = JYOTIGPT_AUTH_COOKIE_SAME_SITE
            cookie_kwargs["secure"] = JYOTIGPT_AUTH_COOKIE_SECURE

        response.set_cookie(key="token", value=token, **cookie_kwargs)

    @staticmethod
    def _build_token(request: Request, user) -> tuple[str, Optional[int]]:
        """Sign a fresh session token for the user.

        Returns ``(token, expires_at)`` where ``expires_at`` is the unix
        timestamp derived from the configured JWT lifetime, or ``None``
        when the lifetime is not a parseable duration.
        """
        expires_delta = parse_duration(request.app.state.config.JWT_EXPIRES_IN)
        expires_at = None
        if expires_delta:
            expires_at = int(time.time()) + int(expires_delta.total_seconds())

        token = create_token(
            data={"id": user.id},
            expires_delta=expires_delta,
        )
        return token, expires_at

    def _open_session(
        self,
        request: Request,
        response: Response,
        user,
        *,
        full_cookie: bool = True,
    ) -> dict:
        """Build the token, set the cookie, and return the session payload."""
        token, expires_at = self._build_token(request, user)
        self._set_token_cookie(
            response, token, expires_at=expires_at, full_cookie=full_cookie
        )
        user_permissions = get_permissions(
            user.id, request.app.state.config.USER_PERMISSIONS
        )
        return self._session_payload(
            user, token, expires_at=expires_at, permissions=user_permissions
        )

    # -- flows ------------------------------------------------------------

    def user_session(self, request: Request, response: Response, user) -> dict:
        """GET / — refresh the current user's token and cookie."""
        return self._open_session(request, response, user)

    def sign_in(self, request: Request, response: Response, form_data: SigninForm):
        """Authenticate and open a session.

        Three credential sources are tried in order of precedence: the
        trusted reverse-proxy header, the default admin account when
        JYOTIGPT_AUTH is disabled, and finally the submitted email +
        password pair.
        """
        if JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER:
            if JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER not in request.headers:
                raise HTTPException(
                    400, detail=ERROR_MESSAGES.INVALID_TRUSTED_HEADER
                )

            trusted_email = request.headers[JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER].lower()
            trusted_name = trusted_email
            if JYOTIGPT_AUTH_TRUSTED_NAME_HEADER:
                trusted_name = request.headers.get(
                    JYOTIGPT_AUTH_TRUSTED_NAME_HEADER, trusted_email
                )
            if not Users.get_user_by_email(trusted_email.lower()):
                self.sign_up(
                    request,
                    response,
                    SignupForm(
                        email=trusted_email, password=str(uuid.uuid4()), name=trusted_name
                    ),
                )
            user = Auths.authenticate_user_by_trusted_header(trusted_email)
        elif JYOTIGPT_AUTH == False:
            admin_email = "admin@localhost"
            admin_password = "admin"

            if Users.get_user_by_email(admin_email.lower()):
                user = Auths.authenticate_user(admin_email.lower(), admin_password)
            else:
                if Users.get_num_users() != 0:
                    raise HTTPException(400, detail=ERROR_MESSAGES.EXISTING_USERS)

                self.sign_up(
                    request,
                    response,
                    SignupForm(
                        email=admin_email, password=admin_password, name="User"
                    ),
                )

                user = Auths.authenticate_user(admin_email.lower(), admin_password)
        else:
            user = Auths.authenticate_user(form_data.email.lower(), form_data.password)

        if user:
            return self._open_session(request, response, user)
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    def sign_up(self, request: Request, response: Response, form_data: SignupForm):
        """Create a user and open a session.

        The first account is promoted to admin and further signups are
        disabled. Password input is rejected past bcrypt's 72-byte limit;
        a new user also fires the signup webhook when one is configured.
        """
        if JYOTIGPT_AUTH:
            if (
                not request.app.state.config.ENABLE_SIGNUP
                or not request.app.state.config.ENABLE_LOGIN_FORM
            ):
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
                )
        else:
            if Users.get_num_users() != 0:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
                )

        user_count = Users.get_num_users()
        if not validate_email_format(form_data.email.lower()):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
            )

        if Users.get_user_by_email(form_data.email.lower()):
            raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

        try:
            role = (
                "admin" if user_count == 0 else request.app.state.config.DEFAULT_USER_ROLE
            )

            if user_count == 0:
                # Disable signup after the first user is created
                request.app.state.config.ENABLE_SIGNUP = False

            # The password passed to bcrypt must be 72 bytes or fewer. If it is longer, it will be truncated before hashing.
            if len(form_data.password.encode("utf-8")) > 72:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.PASSWORD_TOO_LONG,
                )

            hashed = get_password_hash(form_data.password)
            user = Auths.insert_new_auth(
                form_data.email.lower(),
                hashed,
                form_data.name,
                form_data.profile_image_url,
                role,
            )

            if user:
                payload = self._open_session(request, response, user)

                if request.app.state.config.WEBHOOK_URL:
                    post_webhook(
                        request.app.state.JYOTIGPT_NAME,
                        request.app.state.config.WEBHOOK_URL,
                        WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        {
                            "action": "signup",
                            "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                            "user": user.model_dump_json(exclude_none=True),
                        },
                    )

                return payload
            else:
                raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
        except Exception as err:
            log.error(f"Signup error: {str(err)}")
            raise HTTPException(500, detail="An internal error occurred during signup.")

    def add_user(self, form_data):
        """Admin-only user creation, returning a session token."""
        if not validate_email_format(form_data.email.lower()):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
            )

        if Users.get_user_by_email(form_data.email.lower()):
            raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

        try:
            hashed = get_password_hash(form_data.password)
            user = Auths.insert_new_auth(
                form_data.email.lower(),
                hashed,
                form_data.name,
                form_data.profile_image_url,
                form_data.role,
            )

            if user:
                token = create_token(data={"id": user.id})
                return self._session_payload(user, token)
            else:
                raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
        except Exception as err:
            log.error(f"Add user error: {str(err)}")
            raise HTTPException(
                500, detail="An internal error occurred while adding the user."
            )

    def update_password(self, session_user, form_data) -> bool:
        """Verify the current password, then re-hash and store the new one."""
        if JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER:
            raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)
        if session_user:
            user = Auths.authenticate_user(session_user.email, form_data.password)

            if user:
                hashed = get_password_hash(form_data.new_password)
                return Auths.update_user_password_by_id(user.id, hashed)
            else:
                raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_PASSWORD)
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)

    def authenticate_ldap(
        self, request: Request, response: Response, form_data
    ) -> dict:
        """Bind the application account, look the user up, then verify the
        user's own credentials against the directory.

        A successful bind mirrors the other flows' session shape, minus the
        expiry fields. Failures collapse to the generic LDAP error the
        client expects.
        """
        ENABLE_LDAP = request.app.state.config.ENABLE_LDAP
        LDAP_SERVER_LABEL = request.app.state.config.LDAP_SERVER_LABEL
        LDAP_SERVER_HOST = request.app.state.config.LDAP_SERVER_HOST
        LDAP_SERVER_PORT = request.app.state.config.LDAP_SERVER_PORT
        LDAP_ATTRIBUTE_FOR_MAIL = request.app.state.config.LDAP_ATTRIBUTE_FOR_MAIL
        LDAP_ATTRIBUTE_FOR_USERNAME = (
            request.app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME
        )
        LDAP_SEARCH_BASE = request.app.state.config.LDAP_SEARCH_BASE
        LDAP_SEARCH_FILTERS = request.app.state.config.LDAP_SEARCH_FILTERS
        LDAP_APP_DN = request.app.state.config.LDAP_APP_DN
        LDAP_APP_PASSWORD = request.app.state.config.LDAP_APP_PASSWORD
        LDAP_USE_TLS = request.app.state.config.LDAP_USE_TLS
        LDAP_CA_CERT_FILE = request.app.state.config.LDAP_CA_CERT_FILE
        LDAP_CIPHERS = (
            request.app.state.config.LDAP_CIPHERS
            if request.app.state.config.LDAP_CIPHERS
            else "ALL"
        )

        if not ENABLE_LDAP:
            raise HTTPException(400, detail="LDAP authentication is not enabled")

        try:
            tls = Tls(
                validate=CERT_REQUIRED,
                version=PROTOCOL_TLS,
                ca_certs_file=LDAP_CA_CERT_FILE,
                ciphers=LDAP_CIPHERS,
            )
        except Exception as e:
            log.error(f"TLS configuration error: {str(e)}")
            raise HTTPException(400, detail="Failed to configure TLS for LDAP connection.")

        try:
            server = Server(
                host=LDAP_SERVER_HOST,
                port=LDAP_SERVER_PORT,
                get_info=NONE,
                use_ssl=LDAP_USE_TLS,
                tls=tls,
            )
            connection_app = Connection(
                server,
                LDAP_APP_DN,
                LDAP_APP_PASSWORD,
                auto_bind="NONE",
                authentication="SIMPLE" if LDAP_APP_DN else "ANONYMOUS",
            )
            if not connection_app.bind():
                raise HTTPException(400, detail="Application account bind failed")

            search_success = connection_app.search(
                search_base=LDAP_SEARCH_BASE,
                search_filter=f"(&({LDAP_ATTRIBUTE_FOR_USERNAME}={escape_filter_chars(form_data.user.lower())}){LDAP_SEARCH_FILTERS})",
                attributes=[
                    f"{LDAP_ATTRIBUTE_FOR_USERNAME}",
                    f"{LDAP_ATTRIBUTE_FOR_MAIL}",
                    "cn",
                ],
            )

            if not search_success:
                raise HTTPException(400, detail="User not found in the LDAP server")

            entry = connection_app.entries[0]
            username = str(entry[f"{LDAP_ATTRIBUTE_FOR_USERNAME}"]).lower()
            email = entry[f"{LDAP_ATTRIBUTE_FOR_MAIL}"].value  # retrive the Attribute value
            if not email:
                raise HTTPException(400, "User does not have a valid email address.")
            elif isinstance(email, str):
                email = email.lower()
            elif isinstance(email, list):
                email = email[0].lower()
            else:
                email = str(email).lower()

            cn = str(entry["cn"])
            user_dn = entry.entry_dn

            if username == form_data.user.lower():
                connection_user = Connection(
                    server,
                    user_dn,
                    form_data.password,
                    auto_bind="NONE",
                    authentication="SIMPLE",
                )
                if not connection_user.bind():
                    raise HTTPException(400, "Authentication failed.")

                user = Users.get_user_by_email(email)
                if not user:
                    try:
                        user_count = Users.get_num_users()

                        role = (
                            "admin"
                            if user_count == 0
                            else request.app.state.config.DEFAULT_USER_ROLE
                        )

                        user = Auths.insert_new_auth(
                            email=email,
                            password=str(uuid.uuid4()),
                            name=cn,
                            role=role,
                        )

                        if not user:
                            raise HTTPException(
                                500, detail=ERROR_MESSAGES.CREATE_USER_ERROR
                            )

                    except HTTPException:
                        raise
                    except Exception as err:
                        log.error(f"LDAP user creation error: {str(err)}")
                        raise HTTPException(
                            500, detail="Internal error occurred during LDAP user creation."
                        )

                user = Auths.authenticate_user_by_trusted_header(email)

                if user:
                    token = create_token(
                        data={"id": user.id},
                        expires_delta=parse_duration(
                            request.app.state.config.JWT_EXPIRES_IN
                        ),
                    )

                    # Set the cookie token
                    self._set_token_cookie(response, token, full_cookie=False)

                    user_permissions = get_permissions(
                        user.id, request.app.state.config.USER_PERMISSIONS
                    )

                    return self._session_payload(
                        user, token, permissions=user_permissions
                    )
                else:
                    raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)
            else:
                raise HTTPException(400, "User record mismatch.")
        except Exception as e:
            log.error(f"LDAP authentication error: {str(e)}")
            raise HTTPException(400, detail="LDAP authentication failed.")


auths = AuthService()
