from enum import Enum


class UserRole(str, Enum):
    # ADMIN = "admin"
    HOST = "vendor"
    GUEST = "customer"
