from enum import Enum


class UserRole(str, Enum):
    # ADMIN = "admin"
    VENDOR = "Vendor"
    CONSUMER = "Consumer"
