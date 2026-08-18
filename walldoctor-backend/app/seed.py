"""
One-time (idempotent) seed script. Ports the data that used to live as a
hardcoded JS array in the frontend into real database rows, so it can be
edited by a future admin panel instead of a code deploy.

Run with: python -m app.seed
"""
from app.database import Base, engine, SessionLocal
from app import models

CATEGORY_LABELS = {
    "crack_repair": "Crack Repair", "waterproofing": "Waterproofing", "mold_treatment": "Mold Treatment",
    "painting": "Painting", "flooring": "Flooring & Tile", "plastering": "Plastering",
    "electrical": "Electrical", "plumbing": "Plumbing", "carpentry": "Carpentry",
    "ac_service": "AC Service", "pest_control": "Pest Control", "cleaning": "Deep Cleaning",
    "roofing": "Roofing", "false_ceiling": "False Ceiling", "appliance_repair": "Appliance Repair",
    "locksmith": "Locksmith", "gardening": "Gardening", "home_inspection": "Home Inspection",
}

SERVICES = [
    dict(id="cr1", cat="crack_repair", name="QuickFix Crack Sealing", desc="Fast sealing for hairline and minor wall cracks with a smooth touch-up finish.", price=80, price_label="$60 - $100", tier="budget", rating=4.3, reviews=210, duration="same", duration_label="Same day"),
    dict(id="cr2", cat="crack_repair", name="Structural Crack Repair Pro", desc="Deep structural crack diagnosis and reinforced repair for larger or recurring cracks.", price=250, price_label="$180 - $320", tier="premium", rating=4.8, reviews=95, duration="short", duration_label="1-2 days"),
    dict(id="wp1", cat="waterproofing", name="Basic Damp Proofing", desc="Surface-level moisture treatment for early-stage dampness and light seepage.", price=120, price_label="$90 - $150", tier="budget", rating=4.2, reviews=140, duration="short", duration_label="1-2 days"),
    dict(id="wp2", cat="waterproofing", name="Complete Waterproofing System", desc="Full source tracing and multi-layer waterproof coating for chronic seepage issues.", price=475, price_label="$350 - $600", tier="premium", rating=4.9, reviews=210, duration="long", duration_label="3+ days"),
    dict(id="md1", cat="mold_treatment", name="Mold Removal & Sanitize", desc="Anti-fungal cleaning and sanitizing for visible mold patches on walls or ceilings.", price=160, price_label="$120 - $200", tier="mid", rating=4.5, reviews=180, duration="same", duration_label="Same day"),
    dict(id="md2", cat="mold_treatment", name="Advanced Anti-Fungal Treatment", desc="Industrial-grade treatment with moisture-source correction to prevent mold return.", price=320, price_label="$250 - $400", tier="premium", rating=4.7, reviews=88, duration="short", duration_label="1-2 days"),
    dict(id="pt1", cat="painting", name="Single Wall Touch-up Paint", desc="Quick patch and repaint for one wall or small peeling area.", price=60, price_label="$40 - $80", tier="budget", rating=4.1, reviews=300, duration="same", duration_label="Same day"),
    dict(id="pt2", cat="painting", name="Full Room Painting", desc="Complete strip, prime, and repaint for an entire room with even finish.", price=350, price_label="$250 - $450", tier="mid", rating=4.6, reviews=410, duration="short", duration_label="1-2 days"),
    dict(id="pt3", cat="painting", name="Premium Designer Finish", desc="Texture, accent walls, and designer-grade paint finish with premium materials.", price=800, price_label="$600 - $1000", tier="premium", rating=4.9, reviews=75, duration="long", duration_label="3+ days"),
    dict(id="fl1", cat="flooring", name="Tile Crack Patch-up", desc="Replace a small number of cracked or chipped tiles with matching finish.", price=70, price_label="$50 - $90", tier="budget", rating=4.0, reviews=160, duration="same", duration_label="Same day"),
    dict(id="fl2", cat="flooring", name="Full Floor Retiling", desc="Complete floor removal and retiling with leveling for uneven surfaces.", price=600, price_label="$400 - $800", tier="premium", rating=4.8, reviews=130, duration="long", duration_label="3+ days"),
    dict(id="pl1", cat="plastering", name="Patch Plastering", desc="Localized plaster repair for small crumbling or loose patches.", price=95, price_label="$70 - $120", tier="budget", rating=4.2, reviews=190, duration="short", duration_label="1-2 days"),
    dict(id="pl2", cat="plastering", name="Full Wall Re-plastering", desc="Complete plaster removal and reapplication for a solid, even wall base.", price=300, price_label="$220 - $380", tier="mid", rating=4.6, reviews=140, duration="short", duration_label="1-2 days"),
    dict(id="el1", cat="electrical", name="Electrical Repair & Wiring Fix", desc="Diagnose and fix faulty wiring, switches, and minor electrical faults.", price=120, price_label="$80 - $160", tier="mid", rating=4.5, reviews=260, duration="same", duration_label="Same day"),
    dict(id="pb1", cat="plumbing", name="Leak Detection & Pipe Repair", desc="Locate and fix leaking pipes, joints, and fittings around the home.", price=135, price_label="$90 - $180", tier="mid", rating=4.4, reviews=320, duration="same", duration_label="Same day"),
    dict(id="ca1", cat="carpentry", name="Furniture & Door Carpentry", desc="Repair or adjust doors, cabinets, and wooden furniture around the house.", price=160, price_label="$100 - $220", tier="mid", rating=4.3, reviews=150, duration="short", duration_label="1-2 days"),
    dict(id="ac1", cat="ac_service", name="AC Service & Repair", desc="Routine servicing, gas top-up, or repair for split and window AC units.", price=75, price_label="$50 - $100", tier="budget", rating=4.2, reviews=400, duration="same", duration_label="Same day"),
    dict(id="pc1", cat="pest_control", name="Pest Control Treatment", desc="General pest treatment for common household insects and rodents.", price=90, price_label="$60 - $120", tier="budget", rating=4.4, reviews=280, duration="same", duration_label="Same day"),
    dict(id="cl1", cat="cleaning", name="Deep Home Cleaning", desc="Thorough deep clean of floors, walls, kitchen, and bathrooms.", price=105, price_label="$70 - $140", tier="budget", rating=4.6, reviews=500, duration="same", duration_label="Same day"),
    dict(id="rf1", cat="roofing", name="Roof Leak & Repair", desc="Locate and seal roof leaks, cracked tiles, or damaged waterproofing membrane.", price=425, price_label="$300 - $550", tier="premium", rating=4.7, reviews=90, duration="long", duration_label="3+ days"),
    dict(id="fc1", cat="false_ceiling", name="False Ceiling Installation", desc="Custom false ceiling design and installation with integrated lighting.", price=700, price_label="$500 - $900", tier="premium", rating=4.8, reviews=60, duration="long", duration_label="3+ days"),
    dict(id="ap1", cat="appliance_repair", name="Home Appliance Repair", desc="Repair for washing machines, refrigerators, and other home appliances.", price=110, price_label="$70 - $150", tier="mid", rating=4.3, reviews=220, duration="same", duration_label="Same day"),
    dict(id="lk1", cat="locksmith", name="Locksmith & Door Lock Fix", desc="Repair, replace, or rekey door locks and home security fittings.", price=60, price_label="$40 - $80", tier="budget", rating=4.5, reviews=310, duration="same", duration_label="Same day"),
    dict(id="gd1", cat="gardening", name="Garden & Landscaping", desc="Lawn care, plant maintenance, and small landscaping touch-ups.", price=175, price_label="$100 - $250", tier="mid", rating=4.4, reviews=95, duration="short", duration_label="1-2 days"),
    dict(id="hi1", cat="home_inspection", name="Full Home Inspection Report", desc="Room-by-room inspection with a detailed condition report before you renovate or move in.", price=225, price_label="$150 - $300", tier="mid", rating=4.9, reviews=140, duration="short", duration_label="1-2 days"),
]

FIRST_NAMES = ["Rajesh","Meera","David","Sofia","Amit","Chen","Priya","Marcus","Elena","Omar","Grace","Liam","Fatima","Carlos","Nina","Tom","Aisha","Ravi","Julia","Ken","Sarah","Victor","Leila","Noah","Anya"]
LAST_NAMES = ["Sharma","Krishnan","Okafor","Martinez","Verma","Wei","Nair","Bell","Petrova","Hassan","Kim","Reed","Rossi","Singh","Gupta","Khan","Patel","Novak","Diaz","Turner","Silva","Brooks","Ahmed","Costa"]
AREAS = ["Central Springfield","North Springfield","South Springfield","East Springfield","West Springfield","Downtown","Riverside District","Oak Hill","Maple Heights","Lakeside"]
CATEGORY_SUFFIXES = {
    "crack_repair": ["Repairs","Restoration Co.","Structural Fix"], "waterproofing": ["Waterproofing Co.","DampGuard","AquaShield Services"],
    "mold_treatment": ["Mold Solutions","PureAir Treatments","Fungus Free Co."], "painting": ["Painters","Colorworks","Finishing Co."],
    "flooring": ["Flooring Co.","Tile Works","Floor Craft"], "plastering": ["Plastering Co.","Wall Works","Surface Pro"],
    "electrical": ["Electricians","PowerFix","Electrical Services"], "plumbing": ["Plumbers","FlowFix Plumbing","Pipe Works"],
    "carpentry": ["Carpentry Co.","Woodworks","Furniture Repair"], "ac_service": ["AC Services","CoolTech","Climate Care"],
    "pest_control": ["Pest Control","BugFree Solutions","Pest Care Co."], "cleaning": ["Cleaning Co.","SparkleHome","Deep Clean Pros"],
    "roofing": ["Roofing Co.","RoofGuard","TopShield Roofing"], "false_ceiling": ["Ceilings Co.","CeilCraft","Interior Works"],
    "appliance_repair": ["Appliance Repair","FixIt Appliances","Home Appliance Care"], "locksmith": ["Locksmith Co.","KeySafe","SecureLock Services"],
    "gardening": ["Landscaping Co.","Garden Care","GreenScape"], "home_inspection": ["Inspections Co.","HomeCheck","InspectPro"],
}


def _hash_str(s: str) -> int:
    """Port of the frontend's 32-bit string hash, for deterministic demo-provider generation."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return abs(h)


def build_demo_providers() -> list[dict]:
    """NOTE: these are placeholder/demo providers ported from the original frontend's
    fake-data generator, with fake phone numbers. Replace with real vetted providers
    before going live -- see README."""
    providers = []
    for cat in CATEGORY_LABELS:
        suffixes = CATEGORY_SUFFIXES.get(cat, ["Home Services"])
        count = 3 + (_hash_str(cat) % 2)
        for i in range(count):
            seed = f"{cat}_{i}"
            fn = FIRST_NAMES[_hash_str(seed + "f") % len(FIRST_NAMES)]
            ln = LAST_NAMES[_hash_str(seed + "l") % len(LAST_NAMES)]
            suffix = suffixes[i % len(suffixes)]
            rating = round(4.0 + (_hash_str(seed + "r") % 9) / 10, 1)
            reviews = 70 + (_hash_str(seed + "v") % 580)
            experience = 4 + (_hash_str(seed + "e") % 15)
            area = AREAS[_hash_str(seed + "a") % len(AREAS)]
            phone_num = 2000000 + (_hash_str(seed + "p") % 7999999)
            phone_str = str(phone_num)
            providers.append(dict(
                id=seed, cat=cat, name=f"{fn} {ln}", company=f"{ln} {suffix}",
                rating=rating, reviews=reviews, experience=experience, area=area,
                phone_display=f"+1 (555) {phone_str[:3]}-{phone_str[3:7]}",
                phone_link=f"+1555{phone_str}",
            ))
    return providers


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Category).count() > 0:
            print("Already seeded, skipping. Delete the DB file to reseed from scratch.")
            return

        for key, label in CATEGORY_LABELS.items():
            db.add(models.Category(key=key, label_en=label, label_hi=label))

        for s in SERVICES:
            db.add(models.Service(
                id=s["id"], category_key=s["cat"], name=s["name"], description=s["desc"],
                price=s["price"], price_label=s["price_label"], tier=s["tier"],
                rating=s["rating"], reviews=s["reviews"], duration=s["duration"],
                duration_label=s["duration_label"],
            ))

        for p in build_demo_providers():
            db.add(models.Provider(
                id=p["id"], category_key=p["cat"], name=p["name"], company=p["company"],
                area=p["area"], rating=p["rating"], reviews=p["reviews"],
                experience_years=p["experience"], phone_display=p["phone_display"],
                phone_link=p["phone_link"], whatsapp=p["phone_link"].replace("+", ""),
            ))

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
