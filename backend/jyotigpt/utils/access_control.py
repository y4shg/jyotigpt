from typing import Optional, Union, List, Dict, Any
from jyotigpt.models.users import Users, UserModel
from jyotigpt.models.groups import Groups


from jyotigpt.config import DEFAULT_USER_PERMISSIONS
import json


def fill_missing_permissions(
    permissions: Dict[str, Any], default_permissions: Dict[str, Any]
) -> Dict[str, Any]:
    """Recursively backfill any keys absent from ``permissions`` using
    ``default_permissions`` as the template. Nested dicts are merged in
    place; existing values are left untouched.
    """
    for key, value in default_permissions.items():
        if key not in permissions:
            permissions[key] = value
        elif isinstance(value, dict) and isinstance(permissions[key], dict):
            permissions[key] = fill_missing_permissions(permissions[key], value)

    return permissions


def get_permissions(
    user_id: str,
    default_permissions: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge permissions across every group the user belongs to, taking the
    most permissive value on conflict (True wins over False), then ensure
    all default keys are present.
    """

    def combine_permissions(
        permissions: Dict[str, Any], group_permissions: Dict[str, Any]
    ) -> Dict[str, Any]:
        for key, value in group_permissions.items():
            if isinstance(value, dict):
                if key not in permissions:
                    permissions[key] = {}
                permissions[key] = combine_permissions(permissions[key], value)
            else:
                if key not in permissions:
                    permissions[key] = value
                else:
                    permissions[key] = permissions[key] or value
        return permissions

    user_groups = Groups.get_groups_by_member_id(user_id)

    # Deep copy so the caller's default dict is never mutated.
    permissions = json.loads(json.dumps(default_permissions))

    for group in user_groups:
        group_permissions = group.permissions
        permissions = combine_permissions(permissions, group_permissions)

    permissions = fill_missing_permissions(permissions, default_permissions)

    return permissions


def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Dict[str, Any] = {},
) -> bool:
    """Return whether the user is granted ``permission_key`` (a dot-separated
    hierarchy). Any group granting it short-circuits to True; otherwise the
    default permissions are consulted.
    """

    def get_permission(permissions: Dict[str, Any], keys: List[str]) -> bool:
        for key in keys:
            if key not in permissions:
                return False
            permissions = permissions[key]

        return bool(permissions)

    permission_hierarchy = permission_key.split(".")

    user_groups = Groups.get_groups_by_member_id(user_id)

    for group in user_groups:
        group_permissions = group.permissions
        if get_permission(group_permissions, permission_hierarchy):
            return True

    default_permissions = fill_missing_permissions(
        default_permissions, DEFAULT_USER_PERMISSIONS
    )
    return get_permission(default_permissions, permission_hierarchy)


def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
) -> bool:
    if access_control is None:
        return type == "read"

    user_groups = Groups.get_groups_by_member_id(user_id)
    user_group_ids = [group.id for group in user_groups]
    permission_access = access_control.get(type, {})
    permitted_group_ids = permission_access.get("group_ids", [])
    permitted_user_ids = permission_access.get("user_ids", [])

    return user_id in permitted_user_ids or any(
        group_id in permitted_group_ids for group_id in user_group_ids
    )


# Get all users with access to a resource
def get_users_with_access(
    type: str = "write", access_control: Optional[dict] = None
) -> List[UserModel]:
    if access_control is None:
        return Users.get_users()

    permission_access = access_control.get(type, {})
    permitted_group_ids = permission_access.get("group_ids", [])
    permitted_user_ids = permission_access.get("user_ids", [])

    user_ids_with_access = set(permitted_user_ids)

    for group_id in permitted_group_ids:
        group_user_ids = Groups.get_group_user_ids_by_id(group_id)
        if group_user_ids:
            user_ids_with_access.update(group_user_ids)

    return Users.get_users_by_user_ids(list(user_ids_with_access))
