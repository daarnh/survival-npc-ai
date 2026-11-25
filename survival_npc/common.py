"""Tipe dasar bersama: Action, Status, GameState, Decision."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

INF = math.inf


# =============================================================================
# 0. DASAR: Action, GameState, Decision
# =============================================================================
class Action(Enum):
    ATTACK = "ATTACK"          # menyerang musuh
    HEAL = "HEAL"              # memakai medkit
    RETREAT = "RETREAT"        # mundur menjauhi musuh
    TAKE_COVER = "TAKE_COVER"  # mencari perlindungan (= DEFEND pada slide fuzzy)
    RELOAD = "RELOAD"          # mengisi ulang magazen
    EAT = "EAT"                # makan (kelola sumber daya)
    SCAVENGE = "SCAVENGE"      # mencari sumber daya
    REST = "REST"              # memulihkan stamina
    PATROL = "PATROL"          # berjaga / berkeliling


class Status(Enum):            # status node Behaviour Tree
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


@dataclass
class GameState:
    """Informasi s yang diamati NPC pada satu waktu (model formal slide 3)."""
    hp: float = 100.0
    hunger: float = 0.0            # 0 = kenyang, 100 = kelaparan
    stamina: float = 100.0
    ammo: int = 6                  # peluru di magazen
    reserve_ammo: int = 18         # cadangan peluru
    medkits: int = 2
    food: int = 3
    enemy_distance: float = INF    # jarak musuh terdekat (INF = tak ada)
    enemy_count: int = 0
    cover_nearby: bool = False     # ada tempat berlindung di dekat NPC

    @property
    def enemy_present(self) -> bool:
        return self.enemy_count > 0


@dataclass
class Decision:
    action: Action
    status: Optional[Status] = None   # hanya diisi Behaviour Tree
    info: str = ""                    # penjelasan (jalur pohon, skor fuzzy, dst.)


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
