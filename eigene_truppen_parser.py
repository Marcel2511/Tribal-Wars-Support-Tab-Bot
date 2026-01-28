import re
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EigenesDorf:
    dorf_name: str
    koordinaten: str
    truppen: Dict[str, int]
    rest_truppen: Dict[str, int] | None = None

class EigeneTruppenParser:
    @staticmethod
    def parse(text: str) -> List[EigenesDorf]:
        doerfer = []

        # Muster: Dorfname (xxx|yyy) Kxx eigene <truppen...>
        dorf_block_pattern = re.compile(r'(.*?)\((\d{3}\|\d{3})\)\s*K\d+\s*eigene\s*([\d\s]+)')

        for match in dorf_block_pattern.finditer(text):
            name = match.group(1).strip()
            koord = match.group(2)
            truppen_raw = match.group(3).strip()

            # Truppen aufteilen (alle Zahlen)
            truppen_split = list(filter(None, re.split(r'\s+', truppen_raw)))

            if len(truppen_split) < 8:
                print(f"WARNUNG: Dorf '{name}' ({koord}) hat unerwartet wenig Werte: {truppen_split}")
                continue

            truppen = {
                "Speerträger": int(truppen_split[0]),
                "Schwertkämpfer": int(truppen_split[1]),
                "Axtkämpfer": int(truppen_split[2]),
                "Späher": int(truppen_split[3]),
                "Leichte Kavallerie": int(truppen_split[4]),
                "Schwere Kavallerie": int(truppen_split[5]),
                "Rammböcke": int(truppen_split[6]),
                "Katapulte": int(truppen_split[7])
            }

            print(f"Gelesen: {name} ({koord}) -> {truppen}")

            doerfer.append(EigenesDorf(dorf_name=name, koordinaten=koord, truppen=truppen))

        return doerfer