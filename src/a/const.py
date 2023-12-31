#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""constants"""

from enum import Enum, auto
from typing import Dict, Final

PIN_LEN: Final[int] = 6
APP_ID_LEN: Final[int] = 96
APP_SECRET_LEN: Final[int] = 512
APP_NAME_LEN: Final[int] = 256
USERNAME_LEN: Final[int] = 256
BIO_LEN: Final[int] = 1024

ARGON2_SALT_LENGTH: Final[int] = 32
ARGON2_HASH_LENGTH: Final[int] = 512

HASH_LEN: Final[int] = ARGON2_SALT_LENGTH + ARGON2_HASH_LENGTH + 256


class Role(Enum):
    """user roles"""

    user = auto()  # user signed up
    trusted = (
        auto()
    )  # user has been trusted by an owner, makes limits lighter and opens up more services
    mod = (
        auto()
    )  # anything trusted can do, but mods can also delete and modify content and statuses, mark users as unstrusted
    admin = (
        auto()
    )  # everything a mod can do, but they can also delete users ( which in turn deletes all trace of them too )
    owner = auto()  # literally can do anything

    @classmethod
    def json(cls) -> Dict[str, int]:
        """roles as json"""

        return {
            "user": cls.user.value,
            "trusted": cls.trusted.value,
            "mod": cls.mod.value,
            "admin": cls.admin.value,
            "owner": cls.owner.value,
        }
