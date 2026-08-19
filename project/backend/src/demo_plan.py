from __future__ import annotations

from typing import Any
import heapq
import itertools

class Estado:
    def __init__(self, posicion: str, bateria: int, inventario: frozenset, 
                 objetos_suelo: frozenset, puertas_abiertas: frozenset, 
                 paneles_reparados: frozenset, estaciones_activadas: frozenset):
        self.posicion = posicion
        self.bateria = bateria
        self.inventario = inventario
        self.objetos_suelo = objetos_suelo
        self.puertas_abiertas = puertas_abiertas
        self.paneles_reparados = paneles_reparados
        self.estaciones_activadas = estaciones_activadas

    def clave_estado(self):
        # Esta clave excluye la batería para poder aplicar la dominancia en CLOSED
        return (
            self.posicion, 
            self.inventario, 
            self.puertas_abiertas, 
            self.paneles_reparados, 
            self.estaciones_activadas
        )

    def __eq__(self, otro):
        if not isinstance(otro, Estado):
            return False
        return self.clave_estado() == otro.clave_estado() and self.bateria == otro.bateria

    def __hash__(self):
        return hash((self.clave_estado(), self.bateria))

def es_meta(estado: Estado, estaciones_objetivo: set) -> bool:
    return estaciones_objetivo.issubset(estado.estaciones_activadas)   

def obtener_sucesores(estado: Estado, scenario: dict) -> list:
    sucesores = []
    
    costos = scenario.get("action_costs", {})
    c_pickup = costos.get("pickup", 1)
    c_drop = costos.get("drop", 1)
    c_interact = costos.get("interact", 2)
    c_recharge = costos.get("recharge", 3)
    
    robot_data = scenario.get("robot", {})
    capacidad = robot_data.get("cargo_capacity", 3)
    bateria_max = scenario.get("battery_max", 100)

    # --- 1. MOVE ---
    for corredor in scenario.get("corridors", []):
        if corredor["from"] == estado.posicion:
            destino = corredor["to"]
            costo_movimiento = int(corredor["cost"])
            
            puerta = corredor.get("door")
            if puerta and puerta not in estado.puertas_abiertas:
                continue 
                
            if estado.bateria >= costo_movimiento:
                nuevo_estado = Estado(
                    posicion=destino, bateria=estado.bateria - costo_movimiento,
                    inventario=estado.inventario, objetos_suelo=estado.objetos_suelo,
                    puertas_abiertas=estado.puertas_abiertas, paneles_reparados=estado.paneles_reparados,
                    estaciones_activadas=estado.estaciones_activadas
                )
                accion = {"op": "MOVE", "from": estado.posicion, "to": destino, "cost": costo_movimiento}
                sucesores.append((accion, nuevo_estado, costo_movimiento))

    # --- 2. PICKUP ---
    if len(estado.inventario) < capacidad and estado.bateria >= c_pickup:
        for zona_obj, id_obj in estado.objetos_suelo:
            if zona_obj == estado.posicion:
                nuevo_suelo = set(estado.objetos_suelo)
                nuevo_suelo.remove((zona_obj, id_obj))
                nuevo_inv = set(estado.inventario)
                nuevo_inv.add(id_obj)

                if '_' in id_obj and id_obj.split('_')[-1].isdigit():
                    nombre_contrato = id_obj.rsplit('_', 1)[0]
                else:
                    nombre_contrato = id_obj

                nuevo_estado = Estado(
                    posicion=estado.posicion, bateria=estado.bateria - c_pickup,
                    inventario=frozenset(nuevo_inv), objetos_suelo=frozenset(nuevo_suelo),
                    puertas_abiertas=estado.puertas_abiertas, paneles_reparados=estado.paneles_reparados,
                    estaciones_activadas=estado.estaciones_activadas
                )
                accion = {"op": "PICKUP", "item": nombre_contrato, "cost": c_pickup}
                sucesores.append((accion, nuevo_estado, c_pickup))

    # --- 3. DROP ---
    # Permitimos soltar objetos para liberar espacio en el inventario.
    if len(estado.inventario) > 0 and estado.bateria >= c_drop:
        # Nota: En escenarios muy complejos, podríamos restringir el DROP solo 
        # para cuando len(inventario) == capacidad para ahorrar RAM, pero por 
        # seguridad en el parcial, permitimos soltar cualquier objeto.
        for item in estado.inventario:
            nuevo_inv = set(estado.inventario)
            nuevo_inv.remove(item)
            
            nuevo_suelo = set(estado.objetos_suelo)
            nuevo_suelo.add((estado.posicion, item))

            if '_' in item and item.split('_')[-1].isdigit():
                nombre_contrato = item.rsplit('_', 1)[0]
            else:
                nombre_contrato = item

            nuevo_estado = Estado(
                posicion=estado.posicion, bateria=estado.bateria - c_drop,
                inventario=frozenset(nuevo_inv), objetos_suelo=frozenset(nuevo_suelo),
                puertas_abiertas=estado.puertas_abiertas, paneles_reparados=estado.paneles_reparados,
                estaciones_activadas=estado.estaciones_activadas
            )
            accion = {"op": "DROP", "item": nombre_contrato, "cost": c_drop}
            sucesores.append((accion, nuevo_estado, c_drop))

    # --- 4. OPEN_DOOR ---
    if estado.bateria >= c_interact:
        for puerta in scenario.get("doors", []):
            if puerta["id"] not in estado.puertas_abiertas and estado.posicion in puerta["between"]:
                if puerta["key"] in estado.inventario:
                    nuevas_puertas = set(estado.puertas_abiertas)
                    nuevas_puertas.add(puerta["id"])
                    
                    nuevo_estado = Estado(
                        posicion=estado.posicion, bateria=estado.bateria - c_interact,
                        inventario=estado.inventario, objetos_suelo=estado.objetos_suelo,
                        puertas_abiertas=frozenset(nuevas_puertas), paneles_reparados=estado.paneles_reparados,
                        estaciones_activadas=estado.estaciones_activadas
                    )
                    accion = {"op": "INTERACT", "target": puerta["id"], "action": "OPEN_DOOR", "cost": c_interact}
                    sucesores.append((accion, nuevo_estado, c_interact))

    # --- 5. REPAIR ---
    if estado.bateria >= c_interact:
        for panel in scenario.get("panels", []):
            if panel["zone"] == estado.posicion and panel["id"] not in estado.paneles_reparados:
                req_tool = panel["requires"]["tool"]
                req_mat = panel["requires"]["material"]

                has_tool = req_tool in estado.inventario
                mat_id = next((item for item in estado.inventario if item.startswith(req_mat)), None)

                if has_tool and mat_id:
                    nuevos_paneles = set(estado.paneles_reparados)
                    nuevos_paneles.add(panel["id"])
                    nuevo_inv = set(estado.inventario)
                    nuevo_inv.remove(mat_id)

                    nuevo_estado = Estado(
                        posicion=estado.posicion, bateria=estado.bateria - c_interact,
                        inventario=frozenset(nuevo_inv), objetos_suelo=estado.objetos_suelo,
                        puertas_abiertas=estado.puertas_abiertas, paneles_reparados=frozenset(nuevos_paneles),
                        estaciones_activadas=estado.estaciones_activadas
                    )
                    accion = {"op": "INTERACT", "target": panel["id"], "action": "REPAIR", "consumes": req_mat, "cost": c_interact}
                    sucesores.append((accion, nuevo_estado, c_interact))

    # --- 6. ACTIVATE ---
    if estado.bateria >= c_interact:
        for est in scenario.get("stations", []):
            if est["zone"] == estado.posicion and est["id"] not in estado.estaciones_activadas:
                reqs = est.get("requires", {})
                paneles_req = reqs.get("panels_ok", [])
                est_req = reqs.get("stations_online", [])

                if all(p in estado.paneles_reparados for p in paneles_req) and \
                   all(e in estado.estaciones_activadas for e in est_req):
                    
                    nuevas_est = set(estado.estaciones_activadas)
                    nuevas_est.add(est["id"])

                    nuevo_estado = Estado(
                        posicion=estado.posicion, bateria=estado.bateria - c_interact,
                        inventario=estado.inventario, objetos_suelo=estado.objetos_suelo,
                        puertas_abiertas=estado.puertas_abiertas, paneles_reparados=estado.paneles_reparados,
                        estaciones_activadas=frozenset(nuevas_est)
                    )
                    accion = {"op": "INTERACT", "target": est["id"], "action": "ACTIVATE", "cost": c_interact}
                    sucesores.append((accion, nuevo_estado, c_interact))

    # --- 7. RECHARGE ---
    if estado.bateria < bateria_max and estado.bateria >= c_recharge:
        for charger in scenario.get("chargers", []):
            if charger["zone"] == estado.posicion:
                nuevo_estado = Estado(
                    posicion=estado.posicion, bateria=bateria_max,
                    inventario=estado.inventario, objetos_suelo=estado.objetos_suelo,
                    puertas_abiertas=estado.puertas_abiertas, paneles_reparados=estado.paneles_reparados,
                    estaciones_activadas=estado.estaciones_activadas
                )
                accion = {"op": "INTERACT", "target": charger["id"], "action": "RECHARGE", "cost": c_recharge}
                sucesores.append((accion, nuevo_estado, c_recharge))

    return sucesores


def buscar_plan_ia(scenario: dict) -> dict:
    estaciones_objetivo = set(scenario.get("goal", {}).get("stations_online", []))
    
    robot_data = scenario.get("robot", {})
    posicion_inicial = robot_data.get("start", "Z1")
    bateria_inicial = robot_data.get("battery_start", 100)

    objetos_iniciales = set()
    for k in scenario.get("keys", []): objetos_iniciales.add((k["zone"], k["id"]))
    for t in scenario.get("tools", []): objetos_iniciales.add((t["zone"], t["id"]))
    for m in scenario.get("materials", []):
        for i in range(m.get("count", 1)):
            objetos_iniciales.add((m["zone"], f"{m['type']}_{i}"))

    estado_inicial = Estado(
        posicion=posicion_inicial, bateria=bateria_inicial,
        inventario=frozenset(), objetos_suelo=frozenset(objetos_iniciales),
        puertas_abiertas=frozenset(), paneles_reparados=frozenset(),
        estaciones_activadas=frozenset()
    )

    frontera = []
    contador = itertools.count() 
    heapq.heappush(frontera, (0, next(contador), estado_inicial, []))

    # DICCIONARIO para control de dominancia (clave_logica -> mejor_bateria)
    visitados = {}
    iteraciones = 0

    while frontera:
        costo_actual, _, estado_actual, plan = heapq.heappop(frontera)
        iteraciones += 1

        if iteraciones > 1500000:
            return {
                "solution_found": False,
                "total_cost": 0,
                "steps": [],
                "message": "FAILURE: Límite de expansión UCS alcanzado."
            }

        if es_meta(estado_actual, estaciones_objetivo):
            return {
                "solution_found": True,
                "total_cost": costo_actual,
                "steps": plan,
                "message": "¡Misión Completada por la IA mediante UCS!"
            }

        clave = estado_actual.clave_estado()
        
        # LÓGICA DE DOMINANCIA:
        # Si ya llegamos a este mismo estado lógico con IGUAL O MÁS batería, lo descartamos.
        if clave in visitados and visitados[clave] >= estado_actual.bateria:
            continue
            
        # Si no lo descartamos, registramos/actualizamos la mejor batería conocida para este estado lógico.
        visitados[clave] = estado_actual.bateria

        for accion_json, nuevo_estado, costo_accion in obtener_sucesores(estado_actual, scenario):
            nuevo_costo = costo_actual + costo_accion
            nuevo_plan = plan + [accion_json]
            heapq.heappush(frontera, (nuevo_costo, next(contador), nuevo_estado, nuevo_plan))

    return {
        "solution_found": False,
        "total_cost": 0,
        "steps": [],
        "message": "FAILURE: El agente exploró todo el espacio de estados lógicos sin encontrar solución."
    }

def build_demo_plan(scenario: dict[str, Any]) -> dict[str, Any]:
    return buscar_plan_ia(scenario)