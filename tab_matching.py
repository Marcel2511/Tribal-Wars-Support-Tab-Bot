import base64
import copy
import gzip
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from tkinter import ttk
from typing import Dict, List, Optional, Sequence, Tuple
import requests

import pytz
import requests

from distanz_rechner import DistanzRechner
from einheiten import get_laufzeit


@dataclass
class TabMatch:
    herkunft: object
    ziel_koord: str
    abschickzeit: datetime
    ankunftszeit: datetime
    einheiten: Dict[str, int]
    einheit_kuerzel: str

class TabMatching:
    @staticmethod
    def finde_tabs(
        angriffe: List[object],
        eigene_dörfer: List[object],
        tabgroessen_liste: List[Dict[str, int]],
        welt_speed: float = 1.0,
        einheiten_speed: float = 1.0,
        zeitfenster_liste=None,
        boost_level: int = 1
    ) -> List[TabMatch]:
        print(f"[INFO] {len(angriffe)} Angriffe, {len(eigene_dörfer)} eigene Dörfer verarbeitet")

        matches = []
        name_mapping = {
            "speerträger": "Speerträger",
            "schwertkämpfer": "Schwertkämpfer",
            "axtkämpfer": "Axtkämpfer",
            "späher": "Späher",
            "leichte kavallerie": "Leichte Kavallerie",
            "schwere kavallerie": "Schwere Kavallerie",
            "katapulte": "Katapulte"
        }

        laufzeit_einheiten = ["Axtkämpfer", "Späher", "Leichte Kavallerie", "Katapulte", "Schwertkämpfer"]
        tabrelevante_einheiten = ["Speerträger", "Schwertkämpfer", "Schwere Kavallerie"]

        dorf_copies = []
        for dorf in eigene_dörfer:
            dorf_copy = copy.deepcopy(dorf)
            dorf_copy.rest_truppen = copy.deepcopy(dorf.truppen)
            dorf_copies.append(dorf_copy)

        now = datetime.now(pytz.timezone("Europe/Berlin"))

        for angriff in angriffe:
            moegliche_tabs = []
            for dorf in dorf_copies:
                if dorf.koordinaten == angriff.ziel_koord:
                    continue

                distanz = DistanzRechner.berechne_distanz(dorf.koordinaten, angriff.ziel_koord)
                ankunftszeit = angriff.ankunftszeit
                if ankunftszeit.tzinfo is None:
                    ankunftszeit = pytz.timezone("Europe/Berlin").localize(ankunftszeit)

                for tabgroessen in tabgroessen_liste:
                    tab_einheiten = {
                        name_mapping[e.lower()]: menge for e, menge in tabgroessen.items()
                        if e.lower() in name_mapping and name_mapping[e.lower()] in tabrelevante_einheiten
                    }

                    kandidaten = [tab_einheiten.copy()]
                    for zusatz in laufzeit_einheiten:
                        if zusatz not in tab_einheiten and dorf.rest_truppen.get(zusatz, 0) > 0:
                            erweitert = tab_einheiten.copy()
                            erweitert[zusatz] = 1
                            kandidaten.append(erweitert)

                    for kandidat in kandidaten:
                        kandidat_mit_spaeh = kandidat.copy()
                        verfuegbare_spaeh = dorf.rest_truppen.get("Späher", 0)
                        if verfuegbare_spaeh >= 5:
                            kandidat_mit_spaeh["Späher"] = 5  # Add-on
                        elif verfuegbare_spaeh > 0:
                            kandidat_mit_spaeh["Späher"] = verfuegbare_spaeh  # So viele wie möglich

                        # Prüfen, ob die tabrelevanten Einheiten vorhanden sind (Späher NICHT relevant für Ausschluss)
                        if not all(dorf.rest_truppen.get(e, 0) >= m for e, m in kandidat.items()):
                            continue

                        if not kandidat:
                            continue

                        lz = max(get_laufzeit(e, welt_speed, einheiten_speed, boost_level) for e in kandidat)
                        abschick = ankunftszeit - timedelta(minutes=distanz * lz)

                        # Zeitfensterprüfung
                        if abschick < now:
                            continue
                        if not TabMatching.pruefe_in_einem_beliebigen_zeitfenster(abschick, zeitfenster_liste):
                            continue

                        tab = TabMatch(
                            herkunft=dorf,
                            ziel_koord=angriff.ziel_koord,
                            abschickzeit=abschick,
                            ankunftszeit=ankunftszeit,
                            einheiten=kandidat_mit_spaeh,
                            einheit_kuerzel=max(kandidat, key=lambda e: get_laufzeit(e, welt_speed, einheiten_speed, boost_level))
                        )
                        moegliche_tabs.append((abschick, distanz, tab))

            if moegliche_tabs:
                moegliche_tabs.sort(key=lambda t: (t[0], t[1]))
                _, _, bester_match = moegliche_tabs[0]

                for einheit, menge in bester_match.einheiten.items():
                    bester_match.herkunft.rest_truppen[einheit] -= menge

                matches.append(bester_match)

        return matches


    @staticmethod
    def pruefe_in_einem_beliebigen_zeitfenster(ts: datetime, zeitfenster_liste) -> bool:
        """
        True, wenn ts in mindestens einem Fenster liegt.
        Grenzen inklusiv: von <= ts <= bis
        """
        if not zeitfenster_liste:
            # Wenn keine Fenster übergeben werden, gilt: keine Einschränkung
            return True

        for von, bis in zeitfenster_liste:
            if von is None or bis is None:
                continue
            if von <= ts <= bis:
                return True
        return False
    
    @staticmethod
    def send_attackplanner_to_dsu(
        matches: list,
        world: str,
        api_key: str,
        server: str = "de",
        title: str = "Support Tabs",
        sitterMode: bool = False,
        tribe_skill: float = 0.0,
        support_boost: float = 0.0,
        ms: int = 500,
    ) -> dict:
        """
        Sendet Matches an DS-Ultimate AttackPlanner API.
        Rückgabe: JSON dict (enthält u.a. 'edit' bei Erfolg)
        """
        url = "https://ds-ultimate.de/toolAPI/attackPlanner/create"

        if not api_key:
            raise ValueError("DSU API_KEY fehlt.")

        # DE->DS Unit Keys
        ds_names = {
            "Speerträger": "spear",
            "Schwertkämpfer": "sword",
            "Axtkämpfer": "axe",
            "Späher": "spy",
            "Leichte Kavallerie": "light",
            "Schwere Kavallerie": "heavy",
            "Rammböcke": "ram",
            "Katapulte": "catapult",
            # Bogis absichtlich nicht (WIP)
        }

        # Koord->ID map (wie bisher)
        koord_to_id = TabMatching.lade_koord_to_id_map(str(world))

        # Unit keys die wir immer mitsenden (archer/marcher NICHT mitsenden)
        unit_keys = [
            "spear", "sword", "axe", "spy",
            "light", "heavy", "ram", "catapult",
            "knight", "snob",
        ]

        unit_id = {
            "spear": 0,
            "sword": 1,
            "axe": 2,
            "archer": 3,
            "spy": 4,
            "light": 5,
            "marcher": 6,
            "heavy": 7,
            "ram": 8,
            "catapult": 9,
            "knight": 10,
            "snob": 11,
        }

        # URL-encoded payload (items[0][...])
        payload = {
            "world": str(world),
            "server": str(server),
            "title": str(title),
            "sitterMode": "true" if sitterMode else "false",
            "API_KEY": str(api_key),
        }

        for i, match in enumerate(matches):
            start_id = koord_to_id.get(match.herkunft.koordinaten)
            ziel_id = koord_to_id.get(match.ziel_koord)
            if not start_id or not ziel_id:
                # skip, wie bisher beim txt export
                continue

            # slowest_unit: aus einheit_kuerzel (DE) -> DS key
            slowest_unit_key = ds_names.get(match.einheit_kuerzel) or "spear"
            slowest_unit_val = unit_id.get(slowest_unit_key, 0)  # default spear


            base = f"items[{i}]"

            payload[f"{base}[source]"] = str(start_id)
            payload[f"{base}[destination]"] = str(ziel_id)
            payload[f"{base}[slowest_unit]"] = str(int(slowest_unit_val))
            payload[f"{base}[arrival_time]"] = str(int(match.ankunftszeit.timestamp()))  # Sekunden
            payload[f"{base}[type]"] = "0"
            payload[f"{base}[support_boost]"] = str(support_boost)
            payload[f"{base}[tribe_skill]"] = str(tribe_skill)
            payload[f"{base}[ms]"] = str(int(ms))

            # Einheiten: immer alle unit_keys senden, fehlende = 0
            # match.einheiten sind DE-Namen -> DS keys
            einheiten_ds = {}
            for name_de, anzahl in (match.einheiten or {}).items():
                k = ds_names.get(name_de)
                if k:
                    einheiten_ds[k] = int(anzahl)

            for k in unit_keys:
                payload[f"{base}[{k}]"] = str(einheiten_ds.get(k, 0))

        headers = {
            "Accept": "application/json",
        }

        resp = requests.post(url, data=payload, headers=headers, timeout=30)

        # DSU gibt ohne Accept ggf. HTML zurück; wir erzwingen Accept. Trotzdem robust:
        try:
            data = resp.json()
        except Exception:
            text_snippet = (resp.text or "")[:500]
            raise RuntimeError(f"DSU Antwort ist kein JSON (HTTP {resp.status_code}): {text_snippet}")

        if resp.status_code >= 400:
            raise RuntimeError(f"DSU Fehler (HTTP {resp.status_code}): {data}")

        return data

    @staticmethod
    def lade_koord_to_id_map(welt_id: str) -> Dict[str, int]:
        url = f"https://de{welt_id}.die-staemme.de/map/village.txt.gz"
        response = requests.get(url)
        if response.status_code != 200:
            raise RuntimeError(f"Download der Dorfdaten fehlgeschlagen (Status: {response.status_code}, URL: {url})")

        gzip_file = gzip.GzipFile(fileobj=BytesIO(response.content))
        content = gzip_file.read().decode("utf-8")

        koord_to_id_map = {}
        for line in content.strip().splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 4:
                village_id = int(parts[0])
                x = parts[2]
                y = parts[3]
                coord = f"{x}|{y}"
                koord_to_id_map[coord] = village_id

        return koord_to_id_map

    @staticmethod
    def export_dsultimate(matches: list, welt_id: str) -> str:
        ds_names = {
            "Speerträger": "spear",
            "Schwertkämpfer": "sword",
            "Axtkämpfer": "axe",
            "Späher": "spy",
            "Leichte Kavallerie": "light",
            "Schwere Kavallerie": "heavy",
            "Rammböcke": "ram",
            "Katapulte": "catapult"
        }

        koord_to_id = TabMatching.lade_koord_to_id_map(welt_id)
        result = []

        for match in matches:
            start_id = koord_to_id.get(match.herkunft.koordinaten)
            ziel_id = koord_to_id.get(match.ziel_koord)

            if not start_id or not ziel_id:
                continue

            einheit = ds_names.get(match.einheit_kuerzel, match.einheit_kuerzel.lower())

            timestamp_ms = int(match.ankunftszeit.timestamp() * 1000)

            einheiten = {
                ds_names.get(name, ""): base64.b64encode(str(anzahl).encode("utf-8")).decode("utf-8")
                for name, anzahl in match.einheiten.items()
            }

            alle_ds_keys = [
                "spear", "sword", "axe", "archer", "spy",
                "light", "marcher", "heavy", "ram",
                "catapult", "knight", "snob", "militia"
            ]
            einheitencode = "/".join([
                f"{ein}={einheiten.get(ein, 'MA==')}" for ein in alle_ds_keys
            ])

            line = f"{start_id}&{ziel_id}&{einheit}&{timestamp_ms}&0&false&false&{einheitencode}"
            result.append(line)

        return "\n".join(result)
