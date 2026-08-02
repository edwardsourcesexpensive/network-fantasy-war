"""Shared enums used across prototype modules."""
from enum import Enum


class Phase(Enum):
    ENTRY = "entry"
    ACTIONS = "actions"
    ATTACK = "attack"
    EXIT = "exit"
