"""1. Decision Tree: D(n, s) rekursif."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple, Union

from .common import Action, Decision, GameState


# =============================================================================
# 1. DECISION TREE
#    Decision Node  : mengevaluasi kondisi  C_n(s) -> {0, 1}
#    Branch         : jalur True / False
#    Action Node    : tindakan akhir a_n
#    Evaluasi rekursif (slide 5):
#        D(n,s) = a_n               jika n action node
#               = D(n_true,  s)     jika C_n(s) = 1
#               = D(n_false, s)     jika C_n(s) = 0
# =============================================================================
@dataclass
class ActionNode:
    action: Action


@dataclass
class DecisionNode:
    label: str
    condition: Callable[[GameState], bool]
    true_node: "TreeNode"
    false_node: "TreeNode"


TreeNode = Union[ActionNode, DecisionNode]


def A(action: Action) -> ActionNode:
    return ActionNode(action)


def D(label: str, cond: Callable[[GameState], bool],
      t: TreeNode, f: TreeNode) -> DecisionNode:
    return DecisionNode(label, cond, t, f)


def evaluate_tree(node: TreeNode, s: GameState,
                  trace: Optional[List[str]] = None) -> Tuple[Action, List[str]]:
    """Implementasi langsung fungsi rekursif D(n, s)."""
    if trace is None:
        trace = []
    if isinstance(node, ActionNode):                  # n = action node
        return node.action, trace
    result = node.condition(s)                        # C_n(s)
    trace.append(f"{node.label} -> {'True' if result else 'False'}")
    nxt = node.true_node if result else node.false_node
    return evaluate_tree(nxt, s, trace)


def build_slide_tree() -> TreeNode:
    """Pohon persis seperti contoh di slide 5-7."""
    return D("HP < 30?", lambda s: s.hp < 30,
             A(Action.RETREAT),
             D("Distance < 10?", lambda s: s.enemy_distance < 10,
               D("Ammo > 0?", lambda s: s.ammo > 0,
                 A(Action.ATTACK), A(Action.RELOAD)),
               A(Action.PATROL)))


def build_emergency_tree() -> TreeNode:
    """HP kritis dan musuh dekat: bertahan hidup adalah prioritas."""
    return D("cover nearby & jarak >= 5?",
             lambda s: s.cover_nearby and s.enemy_distance >= 5,
             A(Action.TAKE_COVER),
             D("medkit > 0 & jarak >= 5?",
               lambda s: s.medkits > 0 and s.enemy_distance >= 5,
               A(Action.HEAL), A(Action.RETREAT)))


def build_maintenance_tree() -> TreeNode:
    """Tidak ada ancaman: kelola sumber daya & kondisi tubuh."""
    return D("hunger > 70?", lambda s: s.hunger > 70,
             D("food > 0?", lambda s: s.food > 0,
               A(Action.EAT), A(Action.SCAVENGE)),
             D("HP < 50 & medkit?", lambda s: s.hp < 50 and s.medkits > 0,
               A(Action.HEAL),
               D("ammo == 0 & reserve > 0?",
                 lambda s: s.ammo == 0 and s.reserve_ammo > 0,
                 A(Action.RELOAD),
                 D("stamina < 30?", lambda s: s.stamina < 30,
                   A(Action.REST),
                   D("supplies low?",
                     lambda s: s.food < 2 or s.reserve_ammo < 8,
                     A(Action.SCAVENGE), A(Action.PATROL))))))


def build_survival_tree() -> TreeNode:
    """Pohon lengkap untuk NPC survival game."""
    combat = D("HP < 30?", lambda s: s.hp < 30,
               build_emergency_tree(),
               D("ammo > 0?", lambda s: s.ammo > 0,
                 D("gerombolan (>3), jarak >= 5 & ada cover?",
                   lambda s: s.enemy_count > 3 and s.enemy_distance >= 5 and s.cover_nearby,
                   A(Action.TAKE_COVER),
                   A(Action.ATTACK)),
                 D("reserve > 0 & jarak >= 5?",
                   lambda s: s.reserve_ammo > 0 and s.enemy_distance >= 5,
                   A(Action.RELOAD), A(Action.RETREAT))))
    far_enemy = D("HP < 50 & medkit?", lambda s: s.hp < 50 and s.medkits > 0,
                  A(Action.HEAL),
                  D("ammo == 0 & reserve > 0?",
                    lambda s: s.ammo == 0 and s.reserve_ammo > 0,
                    A(Action.RELOAD),
                    build_maintenance_tree()))   # musuh masih jauh: tetap kelola bekal
    return D("enemy present?", lambda s: s.enemy_present,
             D("distance < 10?", lambda s: s.enemy_distance < 10, combat, far_enemy),
             build_maintenance_tree())


class DecisionTreeNPC:
    name = "Decision Tree"

    def __init__(self, root: Optional[TreeNode] = None):
        self.root = root or build_survival_tree()

    def reset(self) -> None:
        pass

    def decide(self, s: GameState) -> Decision:
        action, trace = evaluate_tree(self.root, s)
        return Decision(action, info=" > ".join(trace))
