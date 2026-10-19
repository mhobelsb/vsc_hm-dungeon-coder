from enum import Enum

class JoinResultStatus(str, Enum):
    SUCCESS = "success"

    def __str__(self) -> str:
        return str(self.value)
