import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import pytz


@dataclass
class Unterstützung:
    ziel_koord: str
    ankunftszeit: datetime  # tz-aware Europe/Berlin


class SupportParser:
    @staticmethod
    def _parse_serverzeit(text: str, tz) -> Optional[datetime]:
        # Beispiel: "Serverzeit: 23:21:42 16/01/2026"
        m = re.search(r"Serverzeit:\s*(\d{2}:\d{2}:\d{2})\s+(\d{2}/\d{2}/\d{4})", text)
        if not m:
            return None
        time_s, date_s = m.group(1), m.group(2)
        dt = datetime.strptime(f"{date_s} {time_s}", "%d/%m/%Y %H:%M:%S")
        return tz.localize(dt)

    @staticmethod
    def _parse_ankunft(ankunft_str: str, server_dt: datetime, tz) -> Optional[datetime]:
        s = (ankunft_str or "").strip().lower()

        m = re.search(r"\b(heute|morgen)\s+um\s+(\d{2}:\d{2}:\d{2})\b", s)
        if m:
            tagwort = m.group(1)
            time_s = m.group(2)
            base_date = server_dt.date()
            if tagwort == "morgen":
                base_date = base_date + timedelta(days=1)
            dt_naiv = datetime.strptime(f"{base_date.isoformat()} {time_s}", "%Y-%m-%d %H:%M:%S")
            return tz.localize(dt_naiv)

        # optional: falls absolute Angaben vorkommen
        m = re.search(r"\b(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2}:\d{2})\b", s)
        if m:
            dt_naiv = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d.%m.%y %H:%M:%S")
            return tz.localize(dt_naiv)

        m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2}:\d{2})\b", s)
        if m:
            dt_naiv = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%d.%m.%Y %H:%M:%S")
            return tz.localize(dt_naiv)

        return None

    @staticmethod
    def parse(text: str) -> List[Unterstützung]:
        tz = pytz.timezone("Europe/Berlin")
        server_dt = SupportParser._parse_serverzeit(text, tz) or datetime.now(tz)

        supports: List[Unterstützung] = []

        coord_re = re.compile(r"\((\d{3}\|\d{3})\)")
        ankunft_re = re.compile(
            r"\b(heute\s+um\s+\d{2}:\d{2}:\d{2}|morgen\s+um\s+\d{2}:\d{2}:\d{2}|\d{2}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}|\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2})\b",
            flags=re.IGNORECASE,
        )

        for line in text.splitlines():
            if "Unterstützung" not in line:
                continue

            coord_m = coord_re.search(line)
            if not coord_m:
                continue
            ziel_koord = coord_m.group(1)

            ankunft_m = ankunft_re.search(line)
            if not ankunft_m:
                continue

            ankunft_dt = SupportParser._parse_ankunft(ankunft_m.group(1), server_dt, tz)
            if not ankunft_dt:
                continue

            supports.append(Unterstützung(ziel_koord=ziel_koord, ankunftszeit=ankunft_dt))

        return supports
