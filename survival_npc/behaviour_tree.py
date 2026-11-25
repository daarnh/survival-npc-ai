"""2. Behaviour Tree: Selector, Sequence, status Running."""
from __future__ import annotations

from typing import Callable, Optional

from .common import Action, Decision, GameState, Status


# =============================================================================
# 2. BEHAVIOUR TREE
#    Status node : SUCCESS / FAILURE / RUNNING
#    Selector    : coba anak berurutan sampai salah satu SUCCESS atau RUNNING
#    Sequence    : jalankan anak berurutan; berhenti jika ada FAILURE / RUNNING
# =============================================================================
class Blackboard:
    """Memori bersama antar-node."""
    def __init__(self) -> None:
        self.state: GameState = GameState()
        self.action: Optional[Action] = None
        self.tick: int = 0
        self.info: str = ""


class BTNode:
    def tick(self, bb: Blackboard) -> Status:
        raise NotImplementedError


class Condition(BTNode):
    def __init__(self, name: str, fn: Callable[[GameState], bool]):
        self.name, self.fn = name, fn

    def tick(self, bb: Blackboard) -> Status:
        return Status.SUCCESS if self.fn(bb.state) else Status.FAILURE


class Task(BTNode):
    """Aksi instan: langsung SUCCESS."""
    def __init__(self, action: Action):
        self.action = action

    def tick(self, bb: Blackboard) -> Status:
        bb.action = self.action
        return Status.SUCCESS


class TimedTask(BTNode):
    """Aksi berdurasi (mis. RELOAD, HEAL): RUNNING sampai `duration` tick selesai.
    Bila tidak dipanggil berturut-turut (diinterupsi cabang prioritas lebih
    tinggi) progresnya diulang dari nol."""
    def __init__(self, action: Action, duration: int = 2):
        self.action, self.duration = action, duration
        self._progress, self._last_tick = 0, -10

    def tick(self, bb: Blackboard) -> Status:
        if bb.tick != self._last_tick + 1:
            self._progress = 0
        self._last_tick = bb.tick
        bb.action = self.action
        self._progress += 1
        if self._progress >= self.duration:
            self._progress = 0
            return Status.SUCCESS
        return Status.RUNNING


class Sequence(BTNode):
    def __init__(self, name: str, *children: BTNode):
        self.name, self.children = name, children

    def tick(self, bb: Blackboard) -> Status:
        for child in self.children:
            st = child.tick(bb)
            if st != Status.SUCCESS:      # FAILURE atau RUNNING -> berhenti
                return st
        return Status.SUCCESS


class Selector(BTNode):
    def __init__(self, name: str, *children: BTNode):
        self.name, self.children = name, children

    def tick(self, bb: Blackboard) -> Status:
        for child in self.children:
            st = child.tick(bb)
            if st != Status.FAILURE:      # SUCCESS atau RUNNING -> berhenti
                return st
        return Status.FAILURE


def build_survival_bt() -> BTNode:
    C, T, TT = Condition, Task, TimedTask
    enemy_present = C("enemy present", lambda s: s.enemy_present)

    threat = Sequence("Hadapi Ancaman", enemy_present, Selector(
        "Pilih respons",
        Sequence("Darurat", C("HP < 30", lambda s: s.hp < 30), Selector(
            "Selamatkan diri",
            Sequence("Berlindung", C("cover & jarak>=5", lambda s: s.cover_nearby and s.enemy_distance >= 5),
                     T(Action.TAKE_COVER)),
            Sequence("Heal jauh", C("medkit & jarak>=5", lambda s: s.medkits > 0 and s.enemy_distance >= 5),
                     TT(Action.HEAL, 2)),
            T(Action.RETREAT))),
        Sequence("Heal aman", C("HP<50 & medkit & jarak>=10",
                                lambda s: s.hp < 50 and s.medkits > 0 and s.enemy_distance >= 10),
                 TT(Action.HEAL, 2)),
        Sequence("Reload", C("ammo==0 & reserve & jarak>=5",
                             lambda s: s.ammo == 0 and s.reserve_ammo > 0 and s.enemy_distance >= 5),
                 TT(Action.RELOAD, 2)),
        Sequence("Bertarung", C("jarak<10 & ammo>0 & bukan(gerombolan jauh ber-cover)",
                                lambda s: s.enemy_distance < 10 and s.ammo > 0 and
                                (s.enemy_count <= 3 or s.enemy_distance < 5 or not s.cover_nearby)),
                 T(Action.ATTACK)),
        Sequence("Berlindung 2", C("5<=jarak<10 & cover",
                                   lambda s: 5 <= s.enemy_distance < 10 and s.cover_nearby),
                 T(Action.TAKE_COVER)),
        # jarak >= 10: cabang ini FAILURE -> Selector root lanjut ke "Kelola Sumber Daya"
        Sequence("Mundur", C("jarak<10", lambda s: s.enemy_distance < 10), T(Action.RETREAT))))

    maintain = Selector(
        "Kelola Sumber Daya",
        Sequence("Lapar", C("hunger>70", lambda s: s.hunger > 70),
                 Selector("Cari makan",
                          Sequence("Makan", C("food>0", lambda s: s.food > 0), T(Action.EAT)),
                          T(Action.SCAVENGE))),
        Sequence("Obati", C("HP<50 & medkit", lambda s: s.hp < 50 and s.medkits > 0), TT(Action.HEAL, 2)),
        Sequence("Isi ulang", C("ammo==0 & reserve", lambda s: s.ammo == 0 and s.reserve_ammo > 0),
                 TT(Action.RELOAD, 2)),
        Sequence("Istirahat", C("stamina<30", lambda s: s.stamina < 30), T(Action.REST)),
        Sequence("Cari bekal", C("supplies low", lambda s: s.food < 2 or s.reserve_ammo < 8),
                 T(Action.SCAVENGE)))

    return Selector("ROOT", threat, maintain, T(Action.PATROL))


class BehaviourTreeNPC:
    name = "Behaviour Tree"

    def __init__(self, root: Optional[BTNode] = None):
        self.root = root or build_survival_bt()
        self.bb = Blackboard()

    def reset(self) -> None:
        self.__init__(build_survival_bt())

    def decide(self, s: GameState) -> Decision:
        self.bb.state, self.bb.action = s, None
        self.bb.tick += 1
        status = self.root.tick(self.bb)
        return Decision(self.bb.action or Action.PATROL, status)
