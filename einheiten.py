# einheiten.py

# Basislaufzeiten pro Feld bei Weltgeschwindigkeit = 1 und Einheitengeschwindigkeit = 1
laufzeiten_pro_feld = {
    "Speerträger": 18,
    "Schwertkämpfer": 22,
    "Axtkämpfer": 18,
    "Späher": 9,
    "Leichte Kavallerie": 10,
    "Schwere Kavallerie": 11,
    "Rammböcke": 30,
    "Katapulte": 30
}

# Alias-Namen (z. B. aus GUI, User-Eingaben, DSUltimate) → korrekter Name im Dictionary
einheiten_aliases = {
    "speertraeger": "Speerträger",
    "speerträger": "Speerträger",
    "schwertkaempfer": "Schwertkämpfer",
    "schwertkämpfer": "Schwertkämpfer",
    "axtkaempfer": "Axtkämpfer",
    "axtkämpfer": "Axtkämpfer",
    "spaeher": "Späher",
    "späher": "Späher",
    "leichte kavallerie": "Leichte Kavallerie",
    "schwere kavallerie": "Schwere Kavallerie",
    "rammboecke": "Rammböcke",
    "rammböcke": "Rammböcke",
    "katapulte": "Katapulte"
}


def get_laufzeit(name: str, welt_speed: float = 1.0, einheiten_speed: float = 1.0, boost_multiplier: float = 1.0) -> float:
    # zuerst Normalisierung: lowercase + Sonderzeichen ersetzen
    key = (
        name.strip()
        .lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
    )

    # Mapping prüfen
    if key in einheiten_aliases:
        name = einheiten_aliases[key]
    else:
        # Falls nicht im Mapping: versuche trotzdem ersten Buchstaben groß zu schreiben
        name = key.capitalize()

    if name not in laufzeiten_pro_feld:
        raise ValueError(f"Einheit '{name}' nicht bekannt (aus Originaleingabe: '{key}')")

    return laufzeiten_pro_feld[name] / (welt_speed * einheiten_speed * boost_multiplier)
