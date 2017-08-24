from enum import Enum, auto


class AlertLevels(Enum):
    # Borrowed from Bootstrap
    PRIMARY = auto()
    SECONDARY = auto()
    SUCCESS = auto()
    DANGER = auto()
    WARNING = auto()
    INFO = auto()
    LIGHT = auto()
    DARK = auto()

    @classmethod
    def names(cls):
        return list(cls.__members__.keys())
