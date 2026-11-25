"""4. Markov System: transisi perilaku berbasis probabilitas."""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .common import Action, Decision, GameState
from .fuzzy_logic import mu_crowd, mu_low, mu_near


# =============================================================================
# 4. MARKOV SYSTEM
#    P_ij = P(X_{t+1}=j | X_t=i),  setiap baris: sum_j P_ij = 1
#    pi_{t+1} = pi_t . P
#    Bobot konteks (adapt) mengubah satu baris lalu dinormalisasi ulang, jadi
#    NPC bervariasi namun tetap menyesuaikan diri dengan kondisi permainan.
# =============================================================================
class MarkovChain:
    def __init__(self, states: List[str], matrix: List[List[float]]):
        n = len(states)
        assert len(matrix) == n and all(len(r) == n for r in matrix), "matriks harus n x n"
        for r in matrix:
            assert all(p >= 0 for p in r), "probabilitas tidak boleh negatif"
            assert abs(sum(r) - 1.0) < 1e-9, f"baris harus berjumlah 1: {r}"
        self.states, self.P = states, matrix
        self.index = {s: i for i, s in enumerate(states)}

    def step(self, dist: List[float]) -> List[float]:
        """pi_{t+1} = pi_t P"""
        n = len(self.states)
        return [sum(dist[i] * self.P[i][j] for i in range(n)) for j in range(n)]

    def distribution_after(self, initial: List[float], steps: int) -> List[float]:
        dist = list(initial)
        for _ in range(steps):
            dist = self.step(dist)
        return dist

    def stationary(self, iterations: int = 2000) -> List[float]:
        n = len(self.states)
        return self.distribution_after([1.0 / n] * n, iterations)

    def adapted_row(self, state: str, factors: Optional[Dict[str, float]] = None) -> List[float]:
        row = list(self.P[self.index[state]])
        if factors:
            row = [p * factors.get(s, 1.0) for p, s in zip(row, self.states)]
        total = sum(row)
        if total <= 0:                       # semua probabilitas tertutup -> seragam
            return [1.0 / len(row)] * len(row)
        return [p / total for p in row]      # normalisasi ulang -> sum = 1

    def sample_next(self, state: str, rng: random.Random,
                    factors: Optional[Dict[str, float]] = None) -> str:
        row, r, acc = self.adapted_row(state, factors), rng.random(), 0.0
        for s, p in zip(self.states, row):
            acc += p
            if r < acc:
                return s
        return self.states[-1]


# Matriks dari slide 18: urutan state = [Patrol, Attack, Retreat]
SLIDE_MARKOV = [[0.60, 0.35, 0.05],
                [0.20, 0.70, 0.10],
                [0.50, 0.10, 0.40]]


class MarkovNPC:
    """Mode perilaku dipilih secara probabilistik; mode lalu diterjemahkan
    menjadi aksi konkret sesuai kondisi saat itu."""
    name = "Markov System"

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.chain = MarkovChain(["PATROL", "ATTACK", "RETREAT"], SLIDE_MARKOV)
        self.mode = "PATROL"

    def reset(self) -> None:
        self.mode = "PATROL"

    @staticmethod
    def context_factors(s: GameState) -> Dict[str, float]:
        f = {"PATROL": 1.0, "ATTACK": 1.0, "RETREAT": 1.0}
        low, near = mu_low(s.hp), mu_near(s.enemy_distance)
        if not s.enemy_present:
            f["ATTACK"] = 0.0                       # tidak ada target
            f["RETREAT"] = 0.1 + 2.0 * low          # mode pemulihan saat HP rendah
        else:
            f["PATROL"] *= 1 - 0.8 * near
            f["ATTACK"] *= 1 + near
            f["RETREAT"] *= 1 + 4 * low
            if s.ammo == 0:
                f["ATTACK"] *= 0.15
            crowd = mu_crowd(s)
            f["ATTACK"] *= 1 - 0.6 * crowd
            f["RETREAT"] *= 1 + crowd
        return f

    @staticmethod
    def resolve(mode: str, s: GameState) -> Action:
        if mode == "ATTACK":
            if s.ammo > 0:
                return Action.ATTACK
            if s.reserve_ammo > 0 and s.enemy_distance >= 4:
                return Action.RELOAD
            return Action.RETREAT
        if mode == "RETREAT":
            if not s.enemy_present or s.enemy_distance >= 8:
                if s.medkits > 0 and s.hp < 70:
                    return Action.HEAL
                return Action.REST if s.stamina < 80 else Action.PATROL
            return Action.TAKE_COVER if s.cover_nearby else Action.RETREAT
        # PATROL = rutinitas
        if s.enemy_present and s.enemy_distance < 5:
            return Action.TAKE_COVER if s.cover_nearby else Action.RETREAT
        if s.hunger > 70:
            return Action.EAT if s.food > 0 else Action.SCAVENGE
        if s.ammo == 0 and s.reserve_ammo > 0:
            return Action.RELOAD
        if s.stamina < 30:
            return Action.REST
        if s.food < 2 or s.reserve_ammo < 8:
            return Action.SCAVENGE
        return Action.PATROL

    def decide(self, s: GameState) -> Decision:
        factors = self.context_factors(s)
        row = self.chain.adapted_row(self.mode, factors)
        prev, self.mode = self.mode, self.chain.sample_next(self.mode, self.rng, factors)
        info = f"{prev}->{self.mode} P={[round(p, 2) for p in row]}"
        return Decision(self.resolve(self.mode, s), info=info)
