"""Titik masuk: verifikasi contoh slide, demo skenario, jejak simulasi, benchmark.

Jalankan:  python main.py
"""
from __future__ import annotations

from survival_npc.behaviour_tree import (Blackboard, BehaviourTreeNPC, Condition, Selector, Sequence,
                                          Task, TimedTask)
from survival_npc.common import Action, GameState, Status
from survival_npc.decision_tree import DecisionTreeNPC, build_slide_tree, evaluate_tree
from survival_npc.fuzzy_logic import (FuzzyNPC, fuzzy_choose, fuzzy_infer, mu_high, mu_low, mu_medium,
                                      mu_near, slide_rules)
from survival_npc.hybrid import HybridNPC
from survival_npc.markov import SLIDE_MARKOV, MarkovChain, MarkovNPC
from survival_npc.world import benchmark, run_episode


# =============================================================================
# 7. PENGUJIAN & DEMO
# =============================================================================
def self_tests() -> None:
    """Verifikasi implementasi terhadap contoh hitungan di slide kuliah."""
    # Decision Tree (slide 5-7): HP 80, jarak 5, amunisi 10 -> ATTACK
    act, trace = evaluate_tree(build_slide_tree(), GameState(hp=80, enemy_distance=5, ammo=10, enemy_count=1))
    assert act == Action.ATTACK, act
    print("[OK] Decision Tree slide :", " > ".join(trace), "=>", act.value)

    # Fuzzy (slide 12-15): HP 35, jarak 4 m
    assert abs(mu_low(35) - 0.5) < 1e-9 and abs(mu_medium(35) - 0.5) < 1e-9 and mu_high(35) == 0
    assert abs(mu_near(4) - 0.75) < 1e-9
    s = GameState(hp=35, enemy_distance=4, enemy_count=1)
    scores = fuzzy_infer(s, slide_rules())
    print("[OK] Fuzzy slide         :", {a.value: round(v, 2) for a, v in scores.items()},
          "=> keputusan", fuzzy_choose(scores).value, "(seri dipecah PRIORITY)")
    assert fuzzy_choose(scores) == Action.RETREAT

    # Markov (slide 17-18)
    mc = MarkovChain(["Patrol", "Attack", "Retreat"], SLIDE_MARKOV)
    pi1, pi2 = mc.distribution_after([1, 0, 0], 1), mc.distribution_after([1, 0, 0], 2)
    assert all(abs(a - b) < 1e-9 for a, b in zip(pi1, [0.60, 0.35, 0.05]))
    assert all(abs(a - b) < 1e-9 for a, b in zip(pi2, [0.455, 0.460, 0.085]))
    print(f"[OK] Markov slide        : pi1={[round(x, 3) for x in pi1]}  pi2={[round(x, 3) for x in pi2]}"
          f"  stasioner={[round(x, 3) for x in mc.stationary()]}")

    # Behaviour Tree: semantik Sequence / Selector / Running
    bb = Blackboard()
    bb.tick = 1
    assert Sequence("t", Condition("y", lambda s: True), TimedTask(Action.HEAL, 2)).tick(bb) == Status.RUNNING
    assert Selector("t", Condition("n", lambda s: False), Task(Action.PATROL)).tick(bb) == Status.SUCCESS
    assert Sequence("t", Condition("n", lambda s: False), Task(Action.PATROL)).tick(bb) == Status.FAILURE
    print("[OK] Behaviour Tree      : Sequence/Selector/Running sesuai definisi")


def scenario_demo() -> None:
    scenarios = {
        "Aman, sangat lapar":        GameState(hp=90, hunger=85, stamina=70),
        "Aman, HP rendah, ada medkit": GameState(hp=35, hunger=20),
        "Musuh dekat, HP kritis":    GameState(hp=22, enemy_distance=4, enemy_count=1, cover_nearby=True),
        "Musuh dekat, peluru habis": GameState(hp=80, ammo=0, enemy_distance=6, enemy_count=1),
        "Musuh dekat, HP sehat":     GameState(hp=95, enemy_distance=5, enemy_count=1),
        "Gerombolan musuh (4)":      GameState(hp=70, enemy_distance=7, enemy_count=4, cover_nearby=True),
        "Musuh jauh, HP sedang":     GameState(hp=45, enemy_distance=18, enemy_count=1),
    }
    print(f"\n{'Skenario':<30}{'DecisionTree':<13}{'Behaviour':<18}{'Fuzzy':<12}{'Markov':<12}{'Hybrid':<12}")
    print("-" * 97)
    for name, s in scenarios.items():
        cells = []
        for npc in (DecisionTreeNPC(), BehaviourTreeNPC(), FuzzyNPC(), MarkovNPC(seed=1), HybridNPC(seed=1)):
            d = npc.decide(s)
            cells.append(d.action.value + ("*" if d.status == Status.RUNNING else ""))
        print(f"{name:<30}{cells[0]:<13}{cells[1]:<18}{cells[2]:<12}{cells[3]:<12}{cells[4]:<12}")
    print("(* = Behaviour Tree mengembalikan RUNNING: aksi berdurasi 2 tick)")


if __name__ == "__main__":
    print("=" * 70, "\n VERIFIKASI TERHADAP CONTOH SLIDE\n", "=" * 70, sep="")
    self_tests()

    print("\n" + "=" * 70, "\n KEPUTUSAN TIAP ALGORITMA PADA SKENARIO YANG SAMA\n", "=" * 70, sep="")
    scenario_demo()

    print("\n" + "=" * 70, "\n CONTOH JEJAK SIMULASI HybridNPC (30 tick pertama, seed=1)\n", "=" * 70, sep="")
    r = run_episode(HybridNPC(seed=1), seed=1, max_ticks=300, verbose=30)
    print(f"\nHasil episode: {'HIDUP' if r.alive else 'MATI'} setelah {r.ticks} tick, "
          f"kills={r.kills}, damage diterima={r.damage_taken:.0f}")

    print("\n" + "=" * 70, "\n BENCHMARK: 60 episode x 300 tick per algoritma\n", "=" * 70, sep="")
    benchmark({
        "Decision Tree":            lambda sd: DecisionTreeNPC(),
        "Behaviour Tree":           lambda sd: BehaviourTreeNPC(),
        "Fuzzy Logic":              lambda sd: FuzzyNPC(),
        "Markov System":            lambda sd: MarkovNPC(seed=sd),
        "Hybrid (BT+DT+Fuzzy+MC)":  lambda sd: HybridNPC(seed=sd),
    })
