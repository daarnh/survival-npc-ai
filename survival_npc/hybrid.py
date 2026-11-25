"""5. HybridNPC: Behaviour Tree sebagai orkestrator DT + Fuzzy + Markov."""
from __future__ import annotations

import random
from typing import List, Optional

from .behaviour_tree import BTNode, Blackboard, Condition, Selector, Sequence
from .common import Action, Decision, GameState, Status
from .decision_tree import TreeNode, build_emergency_tree, build_maintenance_tree, evaluate_tree
from .fuzzy_logic import Rule, fuzzy_choose, fuzzy_infer, mu_low_supply, mu_tired, survival_rules
from .markov import MarkovChain


# =============================================================================
# 5. HYBRID NPC  (Behaviour Tree sebagai orkestrator)
#    1. Darurat (HP<30 & musuh dekat)  -> Decision Tree (refleks cepat)
#    2. Ada musuh                      -> Fuzzy Logic (taktik bertahap/halus)
#    3. Kebutuhan mendesak             -> Decision Tree (manajemen sumber daya)
#    4. Aman                           -> Markov (perilaku idle bervariasi)
# =============================================================================
class DecisionTreeTask(BTNode):
    def __init__(self, name: str, tree: TreeNode):
        self.name, self.tree = name, tree

    def tick(self, bb: Blackboard) -> Status:
        bb.action, trace = evaluate_tree(self.tree, bb.state)
        bb.info = f"DT[{self.name}]"
        return Status.SUCCESS


class FuzzyTask(BTNode):
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def tick(self, bb: Blackboard) -> Status:
        scores = fuzzy_infer(bb.state, self.rules)
        bb.action = fuzzy_choose(scores)
        bb.info = "Fuzzy"
        return Status.SUCCESS


class MarkovIdleTask(BTNode):
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.chain = MarkovChain(["PATROL", "SCAVENGE", "REST"],
                                 [[0.70, 0.20, 0.10],
                                  [0.40, 0.50, 0.10],
                                  [0.30, 0.10, 0.60]])
        self.mode = "PATROL"

    def tick(self, bb: Blackboard) -> Status:
        s = bb.state
        tired, lowsup = mu_tired(s), mu_low_supply(s)
        f = {"PATROL": 1.0,
             "SCAVENGE": 1 + 3 * lowsup if lowsup > 0 else 0.5,
             "REST": 1 + 4 * tired if tired > 0 else (0.1 if s.stamina >= 90 else 1.0)}
        self.mode = self.chain.sample_next(self.mode, self.rng, f)
        bb.action, bb.info = Action[self.mode], "Markov"
        return Status.SUCCESS


class HybridNPC:
    name = "Hybrid (BT+DT+Fuzzy+Markov)"

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._build()

    def _build(self) -> None:
        C = Condition
        self.root = Selector(
            "ROOT",
            Sequence("Darurat",
                     C("HP<30 & musuh<10", lambda s: s.hp < 30 and s.enemy_present and s.enemy_distance < 10),
                     DecisionTreeTask("emergency", build_emergency_tree())),
            Sequence("Taktik tempur", C("ada musuh", lambda s: s.enemy_present), FuzzyTask(survival_rules())),
            Sequence("Kebutuhan mendesak",
                     C("butuh makan/heal/reload",
                       lambda s: s.hunger > 70 or (s.hp < 50 and s.medkits > 0)
                       or (s.ammo == 0 and s.reserve_ammo > 0)),
                     DecisionTreeTask("maintenance", build_maintenance_tree())),
            MarkovIdleTask(self.seed))
        self.bb = Blackboard()

    def reset(self) -> None:
        self._build()

    def decide(self, s: GameState) -> Decision:
        self.bb.state, self.bb.action = s, None
        self.bb.tick += 1
        status = self.root.tick(self.bb)
        return Decision(self.bb.action or Action.PATROL, status, self.bb.info)
