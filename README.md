# Tribal Wars Support Tab Bot

Ein Desktop-Tool für "Die Stämme" (Tribal Wars) zur Berechnung optimaler Unterstützungstruppen (Tabs) für die Verteidigung gegen eingehende Angriffe.

## 🎯 Funktionen

- **SOS-Anfragen parsen**: Extrahiert Angriffsinformationen aus Spieltext
- **Eigene Truppen analysieren**: Liest Militäreinheiten aus verschiedenen Dörfern
- **Optimale Unterstützung berechnen**: Ordnet Truppen zur Verteidigung gegen Angriffe zu
- **Export-Funktionalität**: Erstellt formatierten Output für DS Ultimate Tool
- **Zeitfenster-Verwaltung**: Berücksichtigt Ankunftszeiten und Laufzeiten
- **Weltgeschwindigkeiten**: Automatisches Laden der Server-Geschwindigkeiten

## 🚀 Installation & Verwendung

### Option 1: Ausführbare Datei (.exe)

1. **Download von GitHub Releases:**
   - Gehe zu den [Releases](https://github.com/Marcel2511/Tribal-Wars-Support-Tab-Bot/releases)
   - Lade die neueste Version herunter
   - Führe `StammGui.exe` aus
   - Keine Python-Installation erforderlich!

### Option 2: Python-Skript

```bash
# Repository klonen
git clone https://https://github.com/Marcel2511/Tribal-Wars-Support-Tab-Bot
cd Tribal-Wars-Support-Tab-Bot

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv .venv
.venv\Scripts\activate  # Windows
# oder
source .venv/bin/activate  # Linux/Mac

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python StammGui.py
```

## 📋 Abhängigkeiten

- Python 3.10+
- tkinter (GUI Framework)
- requests (HTTP-Anfragen)
- beautifulsoup4 (HTML-Parsing)
- Pillow (Bildverarbeitung)
- pytz (Zeitzone-Unterstützung)

## 🎮 Verwendung

1. **Welt-ID eingeben**: z.B. "221" für de221.die-staemme.de
2. **SOS-Daten einfügen**: Angriffsdaten aus dem Spiel kopieren
3. **Truppen-Übersicht einfügen**: Eigene Truppen aus dem Spiel kopieren (Strg A + Strg C in der Truppenübersicht)
4. **Truppen-Kombinationen konfigurieren**: Gewünschte Tab-Größen festlegen
5. **Zeitfenster setzen**: Beliebig viele Von/Bis-Zeitfenster setzen um Abschickzeitpunkte festzulegen
6. **Tabs berechnen**: Optimale Zuordnung ermitteln
7. **Export**: Ergebnis für DS Ultimate exportieren

### GUI-Elemente

- **Welt-ID**: Server-Nummer (z.B. 221 für de221)
- **SOS-Anfrage**: Textfeld für eingehende Angriffe
- **Eigene Truppen**: Textfeld für verfügbare Einheiten
- **Einheiten-Auswahl**: Checkboxen mit Mengenangaben
- **Zeitfenster**: Von/Bis-Datum für Tab-Timing
- **Berechnen**: Startet die Tab-Berechnung
- **Export**: Speichert Ergebnis als Textdatei

## 📁 Projektstruktur

```
Tribal-Wars-Support-Tab-Bot/
├── StammGui.py                 # Hauptanwendung (GUI)
├── sos_parser.py               # Parser für SOS-Anfragen
├── eigene_truppen_parser.py    # Parser für eigene Truppen
├── tab_matching.py             # Kern-Logik für Tab-Matching
├── distanz_rechner.py          # Entfernungsberechnung
├── einheiten.py                # Einheiten-Definitionen
├── tabverlauf.json             # Gespeicherte Truppen-Kombinationen
├── support.ico                 # Anwendungs-Icon
├── images/                     # Einheiten-Icons
│   ├── unit_axe.webp
│   ├── unit_spear.webp
│   └── ...
├── build/                      # PyInstaller Build-Dateien
├── dist/                       # Fertige .exe-Datei
└── StammGUI.spec               # PyInstaller-Konfiguration
```

## 🔧 Entwicklung

#### Release erstellen

```bash
# Erstelle einen neuen Tag für Release
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions erstellt automatisch:
# 1. Build der .exe-Datei
# 2. GitHub Release mit deutscher Beschreibung
# 3. Upload der .exe-Datei zum Release
```

#### Download für Benutzer

1. Gehe zu [Releases](https://github.com/Marcel2511/Tribal-Wars-Support-Tab-Bot/releases)
2. Lade `StammGui.exe` aus dem neuesten Release herunter
3. Keine weitere Installation nötig!

### Lokale .exe-Datei erstellen

```bash
# Mit vorhandener Spec-Datei (empfohlen)
python -m PyInstaller StammGUI.spec

# Oder manuell
python -m PyInstaller --onefile --windowed --icon=support.ico --add-data "support.ico;." --add-data "images;images" StammGui.py
```

Die fertige .exe-Datei befindet sich dann im `dist/` Ordner.

### Code-Struktur

#### Hauptkomponenten:

- **StammGUI**: Tkinter-basierte Benutzeroberfläche
- **SosParser**: Regex-basierter Parser für Angriffsdaten
- **EigeneTruppenParser**: Parser für Truppen-Übersichten
- **TabMatching**: Algorithmus für optimale Tab-Zuordnung
- **DistanzRechner**: Berechnung von Koordinaten-Entfernungen
- **Einheiten**: Definitionen für Laufzeiten und Laufzeitmanipulation

#### Datenstrukturen:

```python
@dataclass
class Angriff:
    ziel_koord: str
    ankunftszeit: datetime
    einheit: str

@dataclass
class EigenesDorf:
    dorf_name: str
    koordinaten: str
    truppen: Dict[str, int]

@dataclass
class TabMatch:
    herkunft: object
    ziel_koord: str
    abschickzeit: datetime
    ankunftszeit: datetime
    einheiten: Dict[str, int]
    einheit_kuerzel: str
```

## 🎯 Spielkontext

Dieses Tool ist speziell für "Die Stämme" (deutsches Tribal Wars) entwickelt und unterstützt:

- **Koordination defensiver Unterstützung** zwischen Stammesmitgliedern
- **Berechnung optimaler Truppen-Verteilung**
- **Timing von Unterstützung** vor Angriffen
- **Export für DS Ultimate** Browser-Erweiterung

Die Anwendung verarbeitet deutschen Spieltext und koordiniert mit der deutschen Server-Infrastruktur.

## 🌍 Unterstützte Welten

- Alle deutschen Die Stämme Server (de1.die-staemme.de bis de999.die-staemme.de)
- Automatisches Laden von Welt- und Einheiten-Geschwindigkeiten
- Unterstützung für verschiedene Geschwindigkeits-Einstellungen

## 🤝 Beitragen

Beiträge sind willkommen! Bitte erstelle einen Pull Request oder öffne ein Issue.

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Committe deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

## 📞 Support

Bei Fragen oder Problemen:

- Öffne ein [Issue](https://github.com/Marcel2511/Tribal-Wars-Support-Tab-Bot/issues)
- Kontaktiere den Entwickler (Discord: marcel6301)

---

**Hinweis**: Dieses Tool ist für den persönlichen Gebrauch bestimmt und nicht offiziell von InnoGames unterstützt.
