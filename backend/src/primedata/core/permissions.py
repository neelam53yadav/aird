"""
Centralized permissions system for role-based access control.

This module defines all permissions and maps them to workspace roles.
"""

from enum import Enum
from typing import Set

from primedata.db.models import WorkspaceRole


class Permission(str, Enum):
    """Permission enum for all features."""

    # Product Management
    CREATE_PRODUCT = "create_product"
    EDIT_PRODUCT = "edit_product"
    DELETE_PRODUCT = "delete_product"
    VIEW_PRODUCT = "view_product"

    # Team Management
    INVITE_MEMBER = "invite_member"
    REMOVE_MEMBER = "remove_member"
    UPDATE_MEMBER_ROLE = "update_member_role"
    VIEW_MEMBERS = "view_members"

    # Workspace Management
    UPDATE_WORKSPACE = "update_workspace"
    DELETE_WORKSPACE = "delete_workspace"
    MANAGE_BILLING = "manage_billing"

    # Data Sources
    CREATE_DATASOURCE = "create_datasource"
    EDIT_DATASOURCE = "edit_datasource"
    DELETE_DATASOURCE = "delete_datasource"
    VIEW_DATASOURCE = "view_datasource"

    # Pipeline
    TRIGGER_PIPELINE = "trigger_pipeline"
    VIEW_PIPELINE_RUNS = "view_pipeline_runs"

    # Analytics
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_DATA = "export_data"


# Role permissions mapping
ROLE_PERMISSIONS: dict[WorkspaceRole, Set[Permission]] = {
    WorkspaceRole.OWNER: {
        # Owner has all permissions
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.DELETE_PRODUCT,
        Permission.VIEW_PRODUCT,
        Permission.INVITE_MEMBER,
        Permission.REMOVE_MEMBER,
        Permission.UPDATE_MEMBER_ROLE,
        Permission.VIEW_MEMBERS,
        Permission.UPDATE_WORKSPACE,
        Permission.DELETE_WORKSPACE,
        Permission.MANAGE_BILLING,
        Permission.CREATE_DATASOURCE,
        Permission.EDIT_DATASOURCE,
        Permission.DELETE_DATASOURCE,
        Permission.VIEW_DATASOURCE,
        Permission.TRIGGER_PIPELINE,
        Permission.VIEW_PIPELINE_RUNS,
        Permission.VIEW_ANALYTICS,
        Permission.EXPORT_DATA,
    },
    WorkspaceRole.ADMIN: {
        # Admin has all except workspace deletion and billing
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.DELETE_PRODUCT,
        Permission.VIEW_PRODUCT,
        Permission.INVITE_MEMBER,
        Permission.REMOVE_MEMBER,
        Permission.UPDATE_MEMBER_ROLE,
        Permission.VIEW_MEMBERS,
        Permission.UPDATE_WORKSPACE,
        Permission.CREATE_DATASOURCE,
        Permission.EDIT_DATASOURCE,
        Permission.DELETE_DATASOURCE,
        Permission.VIEW_DATASOURCE,
        Permission.TRIGGER_PIPELINE,
        Permission.VIEW_PIPELINE_RUNS,
        Permission.VIEW_ANALYTICS,
        Permission.EXPORT_DATA,
    },
    WorkspaceRole.EDITOR: {
        # Editor can create/edit products and data sources, view members
        Permission.CREATE_PRODUCT,
        Permission.EDIT_PRODUCT,
        Permission.VIEW_PRODUCT,
        Permission.VIEW_MEMBERS,
        Permission.CREATE_DATASOURCE,
        Permission.EDIT_DATASOURCE,
        Permission.VIEW_DATASOURCE,
        Permission.TRIGGER_PIPELINE,
        Permission.VIEW_PIPELINE_RUNS,
        Permission.VIEW_ANALYTICS,
    },
    WorkspaceRole.VIEWER: {
        # Viewer has read-only access
        Permission.VIEW_PRODUCT,
        Permission.VIEW_MEMBERS,
        Permission.VIEW_DATASOURCE,
        Permission.VIEW_PIPELINE_RUNS,
        Permission.VIEW_ANALYTICS,
    },
}


def has_permission(role: WorkspaceRole, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: Workspace role
        permission: Permission to check

    Returns:
        True if role has permission, False otherwise
    """
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(role: WorkspaceRole, permission: Permission) -> None:
    """
    Require that a role has a specific permission, raise exception if not.

    Args:
        role: Workspace role
        permission: Permission to require

    Raises:
        PermissionError: If role doesn't have the required permission
    """
    if not has_permission(role, permission):
        raise PermissionError(f"Role {role.value} does not have permission {permission.value}")


def get_allowed_actions(role: WorkspaceRole) -> Set[Permission]:
    """
    Get all permissions allowed for a role.

    Args:
        role: Workspace role

    Returns:
        Set of permissions allowed for the role
    """
    return ROLE_PERMISSIONS.get(role, set())

