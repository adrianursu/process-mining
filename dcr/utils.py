def get_weapon_type(weapon_name):
    weapon_types = {
        "Glock-18": "Pistol",
        "P2000": "Pistol",
        "USP-S": "Pistol",
        "P250": "Pistol",
        "Desert Eagle": "Pistol",
        "Five-SeveN": "Pistol",
        "Tec-9": "Pistol",
        "CZ75-Auto": "Pistol",
        "Dual Berettas": "Pistol",
        "R8 Revolver": "Pistol",

        "AK-47": "Rifle",
        "M4A4": "Rifle",
        "M4A1-S": "Rifle",
        "M4A1": "Rifle",
        "FAMAS": "Rifle",
        "Galil AR": "Rifle",
        "SG 553": "Rifle",
        "AUG": "Rifle",

        "AWP": "Sniper Rifle",
        "SSG 08": "Sniper Rifle",
        "SCAR-20": "Sniper Rifle",
        "G3SG1": "Sniper Rifle",

        "MP9": "SMG",
        "MP7": "SMG",
        "UMP-45": "SMG",
        "P90": "SMG",
        "PP-Bizon": "SMG",
        "MAC-10": "SMG",
        "MP5-SD": "SMG",

        "MAG-7": "Shotgun",
        "XM1014": "Shotgun",
        "Nova": "Shotgun",
        "Sawed-Off": "Shotgun",

        "Negev": "Machine Gun",
        "M249": "Machine Gun",

        "Knife": "Melee",
        "Zeus x27": "Equipment",
        "HE Grenade": "Grenade",
        "Flashbang": "Grenade",
        "Smoke Grenade": "Grenade",
        "Molotov": "Grenade",
        "Incendiary Grenade": "Grenade",
        "Decoy Grenade": "Grenade",
        "C4 Explosive": "Bomb"
    }

    return weapon_types.get(weapon_name, f"Unknown Weapon Type [{weapon_name}]")
