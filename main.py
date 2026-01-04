from fastapi import FastAPI, Body
from typing import Dict, List, Any

app = FastAPI()

def get_orders_for_role(role: str, weeks: List[Dict]):
    """
    Täiustatud otsustusloogika, mis arvestab 'Supply Line' ehk teel oleva kaubaga.
    """
    # 1. Parameetrid (neid võib tuunida)
    # Beer Game'is on tavaliselt laokulu 0.5 ja backlogi kulu 1.0. 
    # Seega on kasulikum hoida veidi rohkem laovaru kui jääda miinusesse.
    target_inventory = 20  
    
    # Reaktsioonikiirus (0.1 - 1.0). 
    # Väiksem väärtus = stabiilsem süsteem, suurem = kiirem reageerimine.
    alpha_inv = 0.4  # Laoseisu korrigeerimine
    alpha_sl = 0.2   # Supply line (teel oleva kauba) korrigeerimine
    
    # 2. Arvutame hetkeseisu
    current_week = weeks[-1]
    r_data = current_week["roles"][role]
    
    inv = r_data["inventory"]
    backlog = r_data["backlog"]
    incoming = r_data["incoming_orders"]
    
    # 3. Arvutame Supply Line (kui palju kaupa on tellitud, aga pole veel saabunud)
    # Valem: Kõik tehtud tellimused - Kõik saabunud saadetised
    total_ordered = sum(w["orders"][role] for w in weeks[:-1]) if len(weeks) > 1 else 0
    total_received = sum(w["roles"][role]["arriving_shipments"] for w in weeks)
    supply_line = total_ordered - total_received
    
    # 4. Nõudluse prognoos (Eksponentsiaalne silumine)
    # Kasutame viimaste nädalate sissetulevate tellimuste trendi
    if len(weeks) > 1:
        # Kaalutud keskmine: 70% viimane tellimus, 30% eelnev prognoos
        past_orders = [w["roles"][role]["incoming_orders"] for w in weeks]
        expected_demand = (0.7 * incoming) + (0.3 * (sum(past_orders[-3:]) / 3))
    else:
        expected_demand = incoming

    # 5. STERMANI VALEM (The "Smart" part)
    # Me tellime: 
    # + Oodatav nõudlus
    # + (Soovitud laoseis - Hetke netovaru) * Reaktsioonikiirus
    # - (Teel olev kaup, mida me juba ootame) * Teel oleva kauba korrigeerija
    
    net_inventory = inv - backlog
    inventory_gap = target_inventory - net_inventory
    
    # Supply line target: keskmiselt peaks teel olema 2-4 nädala varu (sõltub viiteajast)
    target_supply_line = expected_demand * 2 
    sl_gap = target_supply_line - supply_line
    
    order = expected_demand + (alpha_inv * inventory_gap) + (alpha_sl * sl_gap)

    return max(0, int(round(order)))

@app.post("/api/decision")
async def decision(data: Dict[Any, Any] = Body(...)):
    # Handshake
    if data.get("handshake") is True:
        return {
            "ok": True,
            "student_email": "eesnimi.perenimi@taltech.ee",
            "algorithm_name": "SupplyLineMaster_v2",
            "version": "v1.2.1",
            "supports": {"blackbox": True, "glassbox": True},
            "message": "BeerBot ready"
        }

    weeks = data.get("weeks", [])
    mode = data.get("mode", "blackbox")

    # GlassBox režiimi boonus: 
    # Kui me oleme Factory, saame vaadata Retaileri tegelikku nõudlust
    # See eemaldab "info viite" ja me ei pea ootama, kuni tellimus meieni jõuab.
    
    orders = {
        "retailer": get_orders_for_role("retailer", weeks),
        "wholesaler": get_orders_for_role("wholesaler", weeks),
        "distributor": get_orders_for_role("distributor", weeks),
        "factory": get_orders_for_role("factory", weeks)
    }

    return {"orders": orders}
