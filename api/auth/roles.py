"""Roles y jerarquía (PROMPTS_V6 S01)."""


class Role:
    VIEWER = "viewer"
    ANALYST = "analyst"
    OPERATOR = "operator"
    ADMIN = "admin"


ROLE_HIERARCHY = {
    Role.VIEWER: 1,
    Role.ANALYST: 2,
    Role.OPERATOR: 3,
    Role.ADMIN: 4,
}
