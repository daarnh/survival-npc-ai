"""3. Fuzzy Logic: derajat keanggotaan dan rule strength."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from .common import Action, Decision, GameState, clip


# =============================================================================
# 3. FUZZY LOGIC
#    Fungsi keanggotaan HP (slide 12):  Low / Medium / High, h in [0,100]
#    Near(d) = clip((10 - d) / 8, 0, 1)                     (slide 14)
#    Rule strength = bobot * min(derajat antecedent)         (AND = min)
#    Skor aksi     = max dari semua rule untuk aksi tsb      (OR  = max)
# =============================================================================
def mu_low(h: float) -> float:
    if h <= 20: return 1.0
    if h < 50:  return (50 - h) / 30
    return 0.0


def mu_medium(h: float) -> float:
    if h <= 20: return 0.0
    if h <= 50: return (h - 20) / 30
    if h < 80:  return (80 - h) / 30
    return 0.0


def mu_high(h: float) -> float:
    if h <= 50: return 0.0
    if h < 80:  return (h - 50) / 30
    return 1.0


def mu_near(d: float) -> float:
    return clip((10 - d) / 8)


# Himpunan fuzzy tambahan untuk sumber daya & kondisi lain
def mu_far(d: float) -> float:        return 1.0 - mu_near(d)
def mu_has_ammo(s: GameState) -> float:    return clip(s.ammo / 3)
def mu_no_ammo(s: GameState) -> float:     return 1.0 - mu_has_ammo(s)
def mu_has_reserve(s: GameState) -> float: return clip(s.reserve_ammo / 10)
def mu_has_medkit(s: GameState) -> float:  return clip(float(s.medkits))
def mu_has_food(s: GameState) -> float:    return clip(float(s.food))
def mu_hungry(s: GameState) -> float:      return clip((s.hunger - 40) / 40)
def mu_tired(s: GameState) -> float:       return clip((50 - s.stamina) / 30)
def mu_crowd(s: GameState) -> float:       return clip((s.enemy_count - 1) / 3)
def mu_low_supply(s: GameState) -> float:
    return max(clip((2 - s.food) / 2), clip((15 - s.reserve_ammo) / 15))


@dataclass
class Rule:
    name: str
    conditions: List[Callable[[GameState], float]]
    action: Action
    weight: float = 1.0

    def strength(self, s: GameState) -> float:
        return self.weight * min(c(s) for c in self.conditions)


# Prioritas pemutus seri (tie-break): keselamatan lebih dulu
PRIORITY = [Action.RETREAT, Action.TAKE_COVER, Action.HEAL, Action.RELOAD,
            Action.ATTACK, Action.EAT, Action.SCAVENGE, Action.REST, Action.PATROL]

_hp_low = lambda s: mu_low(s.hp)
_hp_med = lambda s: mu_medium(s.hp)
_hp_high = lambda s: mu_high(s.hp)
_near = lambda s: mu_near(s.enemy_distance)
_far = lambda s: mu_far(s.enemy_distance)


def slide_rules() -> List[Rule]:
    """R1-R3 persis seperti slide 13 (DEFEND dipetakan ke TAKE_COVER)."""
    return [Rule("R1 HP Low & Near -> Retreat", [_hp_low, _near], Action.RETREAT),
            Rule("R2 HP Medium & Near -> Defend", [_hp_med, _near], Action.TAKE_COVER),
            Rule("R3 HP High & Near -> Attack", [_hp_high, _near], Action.ATTACK)]


def survival_rules() -> List[Rule]:
    return [
        Rule("R1 HP Low & Near -> Retreat", [_hp_low, _near], Action.RETREAT),
        Rule("R2 HP Medium & Near -> Defend", [_hp_med, _near], Action.TAKE_COVER, 0.8),
        Rule("R3 HP High & Near & Ammo -> Attack", [_hp_high, _near, mu_has_ammo], Action.ATTACK),
        Rule("R4 HP Medium & Near & Ammo -> Attack", [_hp_med, _near, mu_has_ammo], Action.ATTACK, 0.6),
        Rule("R5 Near & NoAmmo -> Retreat", [_near, mu_no_ammo], Action.RETREAT),
        Rule("R6 Crowd & Near -> TakeCover", [mu_crowd, _near], Action.TAKE_COVER, 0.6),
        Rule("R7 HP Low & Far & Medkit -> Heal", [_hp_low, _far, mu_has_medkit], Action.HEAL),
        Rule("R8 HP Medium & Far & Medkit -> Heal", [_hp_med, _far, mu_has_medkit], Action.HEAL, 0.7),
        Rule("R9 NoAmmo & Far & Reserve -> Reload", [mu_no_ammo, _far, mu_has_reserve], Action.RELOAD),
        Rule("R10 Hungry & Far & Food -> Eat", [mu_hungry, _far, mu_has_food], Action.EAT),
        Rule("R11 Hungry & Far & NoFood -> Scavenge",
             [mu_hungry, _far, lambda s: 1 - mu_has_food(s)], Action.SCAVENGE),
        Rule("R12 LowSupply & Far -> Scavenge", [mu_low_supply, _far], Action.SCAVENGE, 0.6),
        Rule("R13 Tired & Far -> Rest", [mu_tired, _far], Action.REST),
        Rule("R14 Baseline -> Patrol", [_far], Action.PATROL, 0.2),
    ]


def fuzzy_infer(s: GameState, rules: List[Rule]) -> Dict[Action, float]:
    scores: Dict[Action, float] = {}
    for r in rules:
        scores[r.action] = max(scores.get(r.action, 0.0), r.strength(s))
    return scores


def fuzzy_choose(scores: Dict[Action, float]) -> Action:
    """Skor tertinggi menang; bila seri, gunakan PRIORITY."""
    best = max(scores.values(), default=0.0)
    if best <= 0.0:
        return Action.PATROL
    tied = [a for a, v in scores.items() if abs(v - best) < 1e-9]
    return min(tied, key=PRIORITY.index)


class FuzzyNPC:
    name = "Fuzzy Logic"

    def __init__(self, rules: Optional[List[Rule]] = None):
        self.rules = rules or survival_rules()

    def reset(self) -> None:
        pass

    def decide(self, s: GameState) -> Decision:
        scores = fuzzy_infer(s, self.rules)
        top = sorted(((v, a.value) for a, v in scores.items() if v > 0), reverse=True)[:3]
        info = ", ".join(f"{a}={v:.2f}" for v, a in top)
        return Decision(fuzzy_choose(scores), info=info)
