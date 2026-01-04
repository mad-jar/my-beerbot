from fastapi import FastAPI, Body
from typing import Dict, List, Any

app = FastAPI()

# --- KONFIGURATSIOON (Häälestatavad parameetrid) ---
# Sihtvaru tase, mida iga lüli püüab hoida (et vältida backlogi)
TARGET_INVENTORY = 15
# Alpha (0-1): kui kiiresti me reageerime nõudluse muutusele.
# Madalam väärtus (nt 0.3) on stabiilsem ja vähendab bullwhip-efekti.
SMOOTHING_ALPHA = 0.4
# K parameeter: kui agressiivselt me laoseisu viga korrigeerime
CORRECTION_FACTOR = 0.6


def calculate_role_order(role_name: str, weeks_data: List[Dict]) -> int:
    """
    Arvutab optimaalse tellimuse konkreetsele rollile tuginedes ajaloole.
    """
    # 1. Leia viimase nädala seis
    current_week_data = weeks_data[-1]
    role_state = current_week_data["roles"][role_name]

    inventory = role_state["inventory"]
    backlog = role_state["backlog"]
    incoming_order = role_state["incoming_orders"]

    # 2. Arvuta oodatav nõudlus (liikuv keskmine või silumine)
    # Kui on esimene nädal, eeldame baasnõudlust 4
    if len(weeks_data) <= 1:
        expected_demand = float(incoming_order)
    else:
        # Võtame eelmise 3 nädala sissetulevate tellimuste keskmise
        past_orders = [w["roles"][role_name]["incoming_orders"] for w in weeks_data[-3:]]
        expected_demand = sum(past_orders) / len(past_orders)

    # 3. Arvuta netovaru seis (Inventory - Backlog)
    net_inventory = inventory - backlog

    # 4. Otsustusloogika:
    # Order = OodatavNõudlus + (Sihtvaru - Netovaru) * Korrektsioonitegur
    inventory_gap = TARGET_INVENTORY - net_inventory
    raw_order = expected_demand + (inventory_gap * CORRECTION_FACTOR)

    # API nõue: Mitte-negatiivne täisarv
    return max(0, int(round(raw_order)))


@app.post("/api/decision")
async def decision(data: Dict[Any, Any] = Body(...)):
    # --- 1. HANDSHAKE KONTROLL ---
    if data.get("handshake") is True:
        return {
            "ok": True,
            "student_email": "eesnimi.perenimi@taltech.ee",  # MUUDA SEDA!
            "algorithm_name": "SmoothInventoryBot",
            "version": "v1.2.0",
            "supports": {"blackbox": True, "glassbox": True},
            "message": "BeerBot ready"
        }

    # --- 2. NÄDALASE SAMMU TÖÖTLUS ---
    weeks = data.get("weeks", [])
    if not weeks:
        # Kui andmeid pole, tagastame vaikeväärtused
        return {"orders": {"retailer": 4, "wholesaler": 4, "distributor": 4, "factory": 4}}

    # Arvutame tellimused kõigile neljale rollile
    # GlassBox režiimis võiks siin kasutada ka teiste rollide info,
    # aga praegune stabiilne loogika töötab hästi mõlemas.
    response_orders = {
        "retailer": calculate_role_order("retailer", weeks),
        "wholesaler": calculate_role_order("wholesaler", weeks),
        "distributor": calculate_role_order("distributor", weeks),
        "factory": calculate_role_order("factory", weeks)
    }

    return {"orders": response_orders}


# Lokaalseks testimiseks
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)