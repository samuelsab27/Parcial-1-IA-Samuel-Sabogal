"""Tests: demo plan is legal and reaches the mission goal, plus AI theoretical validations."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Agregamos Estado y buscar_plan_ia a la importación original
from demo_plan import build_demo_plan, Estado, buscar_plan_ia  # noqa: E402
from simulator import goal_satisfied, load_scenario, simulate  # noqa: E402


# ==========================================
# PRUEBAS ORIGINALES DEL REPOSITORIO BASE
# ==========================================

def test_demo_plan_reaches_goal() -> None:
    scenario = load_scenario()
    plan = build_demo_plan(scenario)
    assert plan["solution_found"] is True
    assert len(plan["steps"]) > 0
    assert plan["total_cost"] == sum(s["cost"] for s in plan["steps"])

    final = simulate(scenario, plan["steps"])
    assert goal_satisfied(scenario, final), final["stations"]
    assert final["energy_spent"] == plan["total_cost"]


def test_demo_plan_uses_all_ops() -> None:
    scenario = load_scenario()
    plan = build_demo_plan(scenario)
    ops = {s["op"] for s in plan["steps"]}
    assert ops == {"MOVE", "PICKUP", "DROP", "INTERACT"}
    actions = {s.get("action") for s in plan["steps"] if s["op"] == "INTERACT"}
    assert "OPEN_DOOR" in actions
    assert "REPAIR" in actions
    assert "ACTIVATE" in actions
    assert "RECHARGE" in actions


def test_demo_plan_opens_all_doors_and_stations() -> None:
    scenario = load_scenario()
    plan = build_demo_plan(scenario)
    final = simulate(scenario, plan["steps"])
    for d in scenario["doors"]:
        assert final["doors"][d["id"]] == "OPEN"
    for p in scenario["panels"]:
        assert final["panels"][p["id"]] == "OK"
    for s in scenario["stations"]:
        assert final["stations"][s["id"]] == "ONLINE"


# ==========================================
# ENTREGABLE 3: PRUEBAS DE VALIDACIÓN DE IA
# ==========================================

# CASO 1: Estados equivalentes
def test_estados_equivalentes():
    estado_A = Estado(
        posicion="Z1", bateria=100, 
        inventario=frozenset(["KEY_1"]), objetos_suelo=frozenset(), 
        puertas_abiertas=frozenset(), paneles_reparados=frozenset(), estaciones_activadas=frozenset()
    )
    estado_B = Estado(
        posicion="Z1", bateria=100, 
        inventario=frozenset(["KEY_1"]), objetos_suelo=frozenset(), 
        puertas_abiertas=frozenset(), paneles_reparados=frozenset(), estaciones_activadas=frozenset()
    )
    
    assert estado_A == estado_B
    assert hash(estado_A) == hash(estado_B)

# CASO 2: Información relevante
def test_informacion_relevante():
    estado_base = Estado(
        posicion="Z1", bateria=100, 
        inventario=frozenset(["KEY_1"]), objetos_suelo=frozenset(), 
        puertas_abiertas=frozenset(), paneles_reparados=frozenset(), estaciones_activadas=frozenset()
    )
    estado_distinto = Estado(
        posicion="Z1", bateria=100, 
        inventario=frozenset(), objetos_suelo=frozenset(), 
        puertas_abiertas=frozenset(), paneles_reparados=frozenset(), estaciones_activadas=frozenset()
    )
    
    assert estado_base != estado_distinto
    assert hash(estado_base) != hash(estado_distinto)

# CASO 3: Costos diferentes
def test_costos_diferentes():
    escenario_trampa = {
        "robot": {"start": "Z1", "battery_start": 100, "cargo_capacity": 3},
        "battery_max": 100,
        "corridors": [
            {"from": "Z1", "to": "Z2", "cost": 50},
            {"from": "Z1", "to": "Z3", "cost": 5},
            {"from": "Z3", "to": "Z2", "cost": 5}
        ],
        "stations": [{"id": "META", "zone": "Z2"}],
        "goal": {"stations_online": ["META"]},
        "action_costs": {"interact": 2}
    }
    
    resultado = buscar_plan_ia(escenario_trampa)
    
    assert resultado["solution_found"] is True
    assert resultado["total_cost"] == 12

# CASO 4: Sin solución
def test_sin_solucion():
    escenario_imposible = {
        "robot": {"start": "Z1", "battery_start": 10, "cargo_capacity": 3},
        "corridors": [],
        "goal": {"stations_online": ["ESTACION_IMPOSIBLE"]}
    }
    
    resultado = buscar_plan_ia(escenario_imposible)
    
    assert resultado["solution_found"] is False
    assert "FAILURE" in resultado["message"]

# CASO 5: Rutas alternativas (Dominancia)
def test_rutas_alternativas():
    escenario_bateria = {
        "robot": {"start": "Z1", "battery_start": 20, "cargo_capacity": 3},
        "battery_max": 100,
        "corridors": [
            {"from": "Z1", "to": "Z2", "cost": 15},
            {"from": "Z1", "to": "Z3", "cost": 5},  
            {"from": "Z3", "to": "Z2", "cost": 5}
        ],
        "stations": [{"id": "META", "zone": "Z2"}],
        "goal": {"stations_online": ["META"]},
        "action_costs": {"interact": 8}
    }
    
    resultado = buscar_plan_ia(escenario_bateria)
    
    assert resultado["solution_found"] is True
    assert resultado["total_cost"] == 18


# ==========================================
# EJECUCIÓN CONJUNTA
# ==========================================
if __name__ == "__main__":
    # Pruebas originales del repo
    test_demo_plan_reaches_goal()
    test_demo_plan_uses_all_ops()
    test_demo_plan_opens_all_doors_and_stations()
    
    # Pruebas obligatorias del Entregable 3
    test_estados_equivalentes()
    test_informacion_relevante()
    test_costos_diferentes()
    test_sin_solucion()
    test_rutas_alternativas()
    
    print("All demo plan tests AND AI theoretical tests passed successfully.")