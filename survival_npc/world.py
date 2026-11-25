"""6. Dunia survival game sederhana + runner episode & benchmark."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List

from .common import INF, Action, Decision, GameState, Status, clip


# =============================================================================
# 6. DUNIA SURVIVAL GAME (simulasi sederhana untuk menguji NPC)
# =============================================================================
@dataclass
class Enemy:
    hp: float
    dist: float


@dataclass
class EpisodeResult:
    ticks: int
    alive: bool
    kills: int
    hp_end: float
    damage_taken: float


class GameWorld:
    MAG = 6

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        self.hp, self.hunger, self.stamina = 100.0, 0.0, 100.0
        self.ammo, self.reserve, self.medkits, self.food = 6, 18, 2, 3
        self.enemies: List[Enemy] = []
        self.cover = False
        self.kills, self.damage_taken = 0, 0.0

    def observe(self) -> GameState:
        d = min((e.dist for e in self.enemies), default=INF)
        return GameState(self.hp, self.hunger, self.stamina, self.ammo, self.reserve,
                         self.medkits, self.food, d, len(self.enemies), self.cover)

    def _hurt(self, amount: float, in_cover: bool) -> None:
        amount *= 0.4 if in_cover else 1.0
        self.hp -= amount
        self.damage_taken += amount

    def step(self, dec: Decision) -> None:
        a, rng = dec.action, self.rng
        busy = dec.status == Status.RUNNING      # aksi berdurasi masih berjalan
        in_cover, retreat_gain = False, 0.0

        if not busy:
            if a == Action.ATTACK and self.ammo > 0 and self.enemies:
                self.ammo -= 1
                target = min(self.enemies, key=lambda e: e.dist)
                if rng.random() < clip(0.95 - 0.03 * target.dist, 0.4, 0.95):
                    target.hp -= 20
                self.stamina -= 1
            elif a == Action.RELOAD and self.reserve > 0:
                n = min(self.reserve, self.MAG - self.ammo)
                self.ammo, self.reserve = self.ammo + n, self.reserve - n
            elif a == Action.HEAL and self.medkits > 0:
                self.hp, self.medkits = min(100.0, self.hp + 40), self.medkits - 1
            elif a == Action.EAT and self.food > 0:
                self.food, self.hunger = self.food - 1, max(0.0, self.hunger - 50)
            elif a == Action.SCAVENGE:
                r = rng.random()
                if r < 0.45:   self.food += 1
                elif r < 0.90: self.reserve += 4
                else:          self.medkits += 1
                self.stamina -= 4
            elif a == Action.REST:
                self.stamina = min(100.0, self.stamina + 20)
            elif a == Action.RETREAT:
                retreat_gain = 2.5 if self.stamina >= 10 else 1.0
                self.stamina -= 3
            elif a == Action.TAKE_COVER:
                in_cover = self.cover
                self.stamina -= 1
            elif a == Action.PATROL:
                self.stamina -= 1
        self.stamina = max(0.0, self.stamina)

        # --- musuh bergerak & menyerang
        for e in self.enemies:
            e.dist = max(1.0, e.dist + retreat_gain - 1.0)
            if e.dist <= 2.0:
                self._hurt(6, in_cover)
            elif e.dist <= 8.0 and rng.random() < 0.20:
                self._hurt(3, in_cover)
        for e in [e for e in self.enemies if e.hp <= 0]:
            self.kills += 1
            if rng.random() < 0.4:
                self.reserve += 4
        self.enemies = [e for e in self.enemies if e.hp > 0]

        # --- kebutuhan hidup & spawn
        self.hunger = min(100.0, self.hunger + 0.8)
        if self.hunger >= 100:
            self.hp -= 2
            self.damage_taken += 2
        if len(self.enemies) < 4 and rng.random() < 0.06:
            for _ in range(rng.choice([1, 1, 2, 2, 3])):
                self.enemies.append(Enemy(30.0, rng.uniform(14, 24)))
        self.cover = rng.random() < 0.4


def run_episode(npc, seed: int, max_ticks: int = 300, verbose: int = 0) -> EpisodeResult:
    world = GameWorld(seed)
    npc.reset()
    if verbose:
        print(f"{'t':>3} {'HP':>4} {'Hun':>4} {'Sta':>4} {'Amo':>3}/{'Res':<3} {'Med':>3} {'Fod':>3} "
              f"{'Musuh':>14}  Aksi")
    for t in range(1, max_ticks + 1):
        s = world.observe()
        dec = npc.decide(s)
        if t <= verbose:
            en = f"{s.enemy_count}@{s.enemy_distance:.0f}m" if s.enemy_present else "-"
            st = f" ({dec.status.value})" if dec.status == Status.RUNNING else ""
            print(f"{t:>3} {s.hp:>4.0f} {s.hunger:>4.0f} {s.stamina:>4.0f} {s.ammo:>3}/{s.reserve_ammo:<3} "
                  f"{s.medkits:>3} {s.food:>3} {en:>14}  {dec.action.value}{st}  [{dec.info}]")
        world.step(dec)
        if world.hp <= 0:
            return EpisodeResult(t, False, world.kills, 0.0, world.damage_taken)
    return EpisodeResult(max_ticks, True, world.kills, world.hp, world.damage_taken)


def benchmark(factories: Dict[str, Callable[[int], object]], seeds: int = 60, ticks: int = 300) -> None:
    print(f"\n{'Algoritma':<30}{'Survive%':>9}{'Rata2 tick':>12}{'Kills':>8}{'Damage':>9}")
    print("-" * 68)
    for name, make in factories.items():
        res = [run_episode(make(sd), sd, ticks) for sd in range(seeds)]
        n = len(res)
        print(f"{name:<30}{100 * sum(r.alive for r in res) / n:>8.0f}%"
              f"{sum(r.ticks for r in res) / n:>12.1f}{sum(r.kills for r in res) / n:>8.1f}"
              f"{sum(r.damage_taken for r in res) / n:>9.0f}")
