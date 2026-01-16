import sys


def resource_path(relative_path):
    """ Pfad zu Ressourcen (für PyInstaller-kompatible Nutzung) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

import json
import os
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

import pytz
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk

from eigene_truppen_parser import EigeneTruppenParser
from sos_parser import SosParser
from tab_matching import TabMatching
from support_parser import SupportParser
from bisect import bisect_left



class StammGUI:
    if getattr(sys, 'frozen', False):
        # Wenn gebundene .exe (PyInstaller)
        ANWENDER_PFAD = os.path.dirname(sys.executable)
    else:
        # Wenn als .py ausgeführt
        ANWENDER_PFAD = os.path.dirname(os.path.abspath(__file__))

    VERLAUF_DATEI = os.path.join(ANWENDER_PFAD, "tabverlauf.json")
    CONFIG_DATEI = os.path.join(ANWENDER_PFAD, "config.json")

    def __init__(self, root):
        self.tk_root = root
        self.tk_root.title("Die Stämme Tab-Tool V3.0 by Marcel Wollbaum")

        self.matches = []
        self.tabgroessen_liste = []
        self.export_button = None
        self.welt_speed = 1.0
        self.einheiten_speed = 1.0
        self.welt_id = ""
        self.boost_level = 0
        self.zeitfenster_liste = []
        self.zeitfenster_tree = None 

        self.build_gui()
        self.lade_tabverlauf()
        self.dsu_api_key = ""
        self.archer_enabled = False
        self.lade_config()

    def build_gui(self):
        self.text_fields = {}
        labels = ["SOS Anfrage", "Eigene Truppen", "Unterstützungen"]
        for idx, label in enumerate(labels):
            ttk.Label(self.tk_root, text=label + ":").grid(row=idx, column=0, sticky="nw", padx=5, pady=(2, 2))
            text = tk.Text(self.tk_root, width=60, height=3)
            text.grid(row=idx, column=1, padx=5, pady=(2, 2))
            self.text_fields[label] = text

        ttk.Label(self.tk_root, text="Welt-ID (z.B. 236):").grid(row=0, column=2, sticky="nw", padx=5, pady=(2, 2))
        self.welt_id_entry = ttk.Entry(self.tk_root, width=5)
        self.welt_id_entry.grid(row=0, column=3, sticky="nw", padx=5, pady=(2, 2))

        ttk.Label(self.tk_root, text="LZ-Multiplikator(%):").grid(row=1, column=2, sticky="nw", padx=5, pady=(2, 2))
        self.boost_entry = ttk.Entry(self.tk_root, width=5)
        self.boost_entry.insert(0, "0")
        self.boost_entry.grid(row=1, column=3, sticky="nw", padx=5, pady=(2, 2))

        ttk.Label(self.tk_root, text="Support-Filter (+Sek. nach Angriff):").grid(row=2, column=2, sticky="nw", padx=5, pady=(2, 2))
        self.support_filter_seconds_entry = ttk.Entry(self.tk_root, width=5)
        self.support_filter_seconds_entry.insert(0, "0")
        self.support_filter_seconds_entry.grid(row=2, column=3, sticky="nw", padx=5, pady=(2, 2))

        self.einheiten = {
            "Speerträger": "unit_spear.webp",
            "Schwertkämpfer": "unit_sword.webp",
            "Axtkämpfer": "unit_axe.webp",
            "Späher": "unit_spy.webp",
            "Leichte Kavallerie": "unit_light.webp",
            "Schwere Kavallerie": "unit_heavy.webp",
            "Rammböcke": "unit_ram.webp",
            "Katapulte": "unit_catapult.webp"
        }

        self.checkbox_vars = {}
        self.entry_fields = {}
        self.image_refs = {}
        self.tab_config_display = None

        unit_frame = ttk.LabelFrame(self.tk_root, text="Einheiten Auswahl")
        unit_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        for idx, (name, img_file) in enumerate(self.einheiten.items()):
            var = tk.BooleanVar()
            self.checkbox_vars[name] = var

            try:
                path = resource_path(os.path.join("images", img_file))
                img = Image.open(path).resize((30, 30))
                img_tk = ImageTk.PhotoImage(img)
                self.image_refs[name] = img_tk
            except Exception as e:
                print(f"Bildproblem bei {img_file}: {e}")
                continue

            row = idx // 4
            col = (idx % 4) * 2

            cb = tk.Checkbutton(unit_frame, text=name, variable=var, image=self.image_refs[name], compound="left")
            cb.grid(row=row, column=col, padx=5, pady=5, sticky="w")

            entry = ttk.Entry(unit_frame, width=5)
            entry.grid(row=row, column=col + 1, padx=5, pady=5, sticky="w")
            self.entry_fields[name] = entry

        ttk.Button(unit_frame, text="+ Kombination hinzufügen", command=self.tab_kombi_hinzufuegen).grid(row=3, column=0, columnspan=2, pady=10, sticky="w")
        self.tab_config_display = tk.Listbox(unit_frame, height=5, width=65)
        self.tab_config_display.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5)

        button_frame = ttk.Frame(unit_frame)
        button_frame.grid(row=4, column=4, sticky="ne", padx=5)
        ttk.Button(button_frame, text="Tabkombination löschen", width=22, command=self.tab_kombi_loeschen).pack(side="top", pady=(0, 5))
        ttk.Button(button_frame, text="Verlauf löschen", width=22, command=self.verlauf_loeschen).pack(side="top")

        bottom_frame = ttk.LabelFrame(self.tk_root, text="Zeitfenster")
        bottom_frame.grid(row=4, column=0, columnspan=5, pady=20, padx=10, sticky="ew")

        # Damit Treeview sauber strecken kann
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(1, weight=1)

        # --- Eingabezeile (row 0) ---
        ttk.Label(bottom_frame, text="Von:").grid(row=0, column=0, padx=(5, 2), sticky="w")
        self.from_entry = ttk.Entry(bottom_frame, width=20)
        self.from_entry.grid(row=0, column=1, padx=(0, 2), sticky="w")
        ttk.Button(bottom_frame, text="Wählen", command=lambda: self.datum_popup("Von", self.from_entry)).grid(row=0, column=2, padx=(0, 2))
        ttk.Button(bottom_frame, text="X", width=2, command=lambda: self.from_entry.delete(0, tk.END)).grid(row=0, column=3, padx=(0, 10))

        ttk.Label(bottom_frame, text="Bis:").grid(row=0, column=4, padx=(10, 2), sticky="w")
        self.to_entry = ttk.Entry(bottom_frame, width=20)
        self.to_entry.grid(row=0, column=5, padx=(0, 2), sticky="w")
        ttk.Button(bottom_frame, text="Wählen", command=lambda: self.datum_popup("Bis", self.to_entry)).grid(row=0, column=6, padx=(0, 2))
        ttk.Button(bottom_frame, text="X", width=2, command=lambda: self.to_entry.delete(0, tk.END)).grid(row=0, column=7, padx=(0, 10))

        ttk.Button(
            bottom_frame,
            text="Zeitfenster hinzufügen",
            command=self.zeitfenster_hinzufuegen
        ).grid(row=0, column=8, padx=(10, 10), ipadx=10, sticky="e")

        # --- Liste (row 1) ---
        tree_frame = ttk.Frame(bottom_frame)
        tree_frame.grid(row=1, column=0, columnspan=9, sticky="nsew", padx=5, pady=(10, 5))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.zeitfenster_tree = ttk.Treeview(
            tree_frame,
            columns=("von", "bis"),
            show="headings",
            height=5,
            selectmode="browse"
        )
        self.zeitfenster_tree.heading("von", text="Von")
        self.zeitfenster_tree.heading("bis", text="Bis")
        self.zeitfenster_tree.column("von", width=240, anchor="w")
        self.zeitfenster_tree.column("bis", width=240, anchor="w")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.zeitfenster_tree.yview)
        self.zeitfenster_tree.configure(yscrollcommand=scroll.set)

        self.zeitfenster_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        # --- Button-Leiste (row 2) ---
        action_frame = ttk.Frame(bottom_frame)
        action_frame.grid(row=2, column=0, columnspan=9, sticky="ew", padx=5, pady=(5, 8))
        action_frame.columnconfigure(0, weight=1)

        # links
        left_btns = ttk.Frame(action_frame)
        left_btns.grid(row=0, column=0, sticky="w")

        ttk.Button(left_btns, text="Entfernen", command=self.zeitfenster_entfernen).pack(side="left", padx=(0, 6))
        ttk.Button(left_btns, text="Alle löschen", command=self.zeitfenster_alle_loeschen).pack(side="left")

        # rechts
        right_btns = ttk.Frame(action_frame)
        right_btns.grid(row=0, column=1, sticky="e")

        ttk.Button(right_btns, text="Menü", command=self.zeige_menue_fenster).pack(
            side="left", padx=(0, 8), ipadx=20, ipady=6
        )
        ttk.Button(right_btns, text="Kontakt", command=self.zeige_kontakt_fenster).pack(
            side="left", padx=(0, 12), ipadx=20, ipady=6
        )

        ttk.Button(right_btns, text="Berechne Tabs", command=self.berechne_tabs).pack(
            side="left", padx=(0, 8), ipadx=25, ipady=6
        )

        self.export_button = ttk.Button(right_btns, text="Exportieren", command=self.exportiere, state="disabled")
        self.export_button.pack(side="left", ipadx=20, ipady=6)


    def zeige_kontakt_fenster(self):
        popup = tk.Toplevel(self.tk_root)
        popup.title("Kontakt")
        popup.geometry("480x260")
        popup.resizable(False, False)

        container = ttk.Frame(popup, padding=12)
        container.pack(fill="both", expand=True)

        # === Daten ===
        autor = "Marcel Wollbaum"
        version = "V3.0"
        discord_handle = "DEIN_DISCORD_HANDLE"  # <-- hier eintragen
        github_repo = "https://github.com/Marcel2511/Tribal-Wars-Support-Tab-Bot"

        # === Überschrift ===
        ttk.Label(
            container,
            text="Die Stämme SOS Tool",
            font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        ttk.Label(container, text=f"Version: {version}").grid(
            row=1, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(container, text=f"Autor: {autor}").grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        # === Discord ===
        ttk.Label(container, text="Discord:").grid(row=3, column=0, sticky="w")
        ttk.Label(container, text=discord_handle).grid(
            row=3, column=1, sticky="w", padx=(6, 6)
        )
        ttk.Button(
            container,
            text="Kopieren",
            command=lambda: self._copy_to_clipboard(discord_handle)
        ).grid(row=3, column=2, sticky="e")

        # === GitHub ===
        ttk.Label(container, text="GitHub:").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(container, text=github_repo).grid(
            row=4, column=1, sticky="w", padx=(6, 6), pady=(10, 0)
        )

        gh_btns = ttk.Frame(container)
        gh_btns.grid(row=4, column=2, sticky="e", pady=(10, 0))
        ttk.Button(
            gh_btns,
            text="Kopieren",
            command=lambda: self._copy_to_clipboard(github_repo)
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            gh_btns,
            text="Öffnen",
            command=lambda: self._open_url(github_repo)
        ).pack(side="left")

        # === Schließen ===
        ttk.Button(
            container,
            text="Schließen",
            command=popup.destroy
        ).grid(row=6, column=2, sticky="e", pady=(20, 0))

        container.columnconfigure(1, weight=1)

    
    def lade_config(self):
        try:
            if os.path.exists(self.CONFIG_DATEI):
                with open(self.CONFIG_DATEI, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.dsu_api_key = (cfg.get("dsu_api_key") or "")
                self.archer_enabled = bool(cfg.get("archer_enabled", False))
        except Exception as e:
            print(f"Fehler beim Laden der Config: {e}")

    def speichere_config(self):
        try:
            cfg = {
                "dsu_api_key": self.dsu_api_key,
                "archer_enabled": self.archer_enabled,
            }
            with open(self.CONFIG_DATEI, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")

    def _copy_to_clipboard(self, text: str):
        try:
            self.tk_root.clipboard_clear()
            self.tk_root.clipboard_append(text)
        except Exception as e:
            print(f"Clipboard Fehler: {e}")

    def _open_url(self, url: str):
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            print(f"Browser öffnen fehlgeschlagen: {e}")  

    def zeige_menue_fenster(self):
        popup = tk.Toplevel(self.tk_root)
        popup.title("Menü")
        popup.geometry("520x320")
        popup.resizable(False, False)

        container = ttk.Frame(popup, padding=12)
        container.pack(fill="both", expand=True)

        # --- DSU API Key ---
        ttk.Label(container, text="DSU-API-Key", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="Hinweis: Den DSU-API-Key bekommst du auf dem Discord (DEIN_DISCORD_HANDLE) oder direkt bei mir via Discord.",
            wraplength=490
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 10))

        key_var = tk.StringVar(value=self.dsu_api_key)
        show_var = tk.BooleanVar(value=False)

        key_entry = ttk.Entry(container, textvariable=key_var, width=55, show="*")
        key_entry.grid(row=2, column=0, columnspan=2, sticky="w")

        def toggle_show():
            key_entry.config(show="" if show_var.get() else "*")

        ttk.Checkbutton(container, text="anzeigen", variable=show_var, command=toggle_show).grid(row=2, column=2, sticky="e", padx=(8, 0))

        def speichern():
            self.dsu_api_key = key_var.get().strip()
            self.speichere_config()
            popup.title("Menü (API-Key gespeichert)")
            popup.after(1200, lambda: popup.title("Menü"))

        def loeschen():
            self.dsu_api_key = ""
            key_var.set("")
            self.speichere_config()
            popup.title("Menü (API-Key gelöscht)")
            popup.after(1200, lambda: popup.title("Menü"))

        btnrow = ttk.Frame(container)
        btnrow.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 14))
        ttk.Button(btnrow, text="Speichern", command=speichern).pack(side="left", padx=(0, 8))
        ttk.Button(btnrow, text="Löschen", command=loeschen).pack(side="left")

        # --- Bogenschützen Checkbox ---
        ttk.Label(container, text="Work in Progress", font=("Segoe UI", 11, "bold")).grid(row=4, column=0, sticky="w", pady=(8, 0))

        archer_var = tk.BooleanVar(value=self.archer_enabled)

        def set_archer():
            self.archer_enabled = bool(archer_var.get())
            self.speichere_config()

        ttk.Checkbutton(
            container,
            text="Bogenschützen aktivieren (Work in Progress)",
            variable=archer_var,
            command=set_archer
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))

        ttk.Label(
            container,
            text="Hinweis: Diese Option ist noch nicht final und kann sich im Verhalten ändern.",
            wraplength=490
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))

        ttk.Button(container, text="Schließen", command=popup.destroy).grid(row=7, column=2, sticky="e", pady=(18, 0))

        container.columnconfigure(0, weight=1)


    def tab_kombi_hinzufuegen(self):
        kombi = {}
        beschreibung = []
        for name, entry in self.entry_fields.items():
            if self.checkbox_vars[name].get():
                try:
                    menge = int(entry.get())
                    if menge > 0:
                        kombi[name] = menge
                        beschreibung.append(f"{menge}x {name}")
                except ValueError:
                    continue
        if kombi:
            self.tabgroessen_liste.append(kombi)
            self.tab_config_display.insert(tk.END, ", ".join(beschreibung))
            self.speichere_tabverlauf()

    def tab_kombi_loeschen(self):
        auswahl = self.tab_config_display.curselection()
        for index in reversed(auswahl):
            self.tab_config_display.delete(index)
            del self.tabgroessen_liste[index]
            self.speichere_tabverlauf()

    def lade_tabverlauf(self):
        try:
            if os.path.exists(self.VERLAUF_DATEI):
                with open(self.VERLAUF_DATEI, "r", encoding="utf-8") as f:
                    daten = json.load(f)
                    for kombi in daten:
                        self.tabgroessen_liste.append(kombi)
                        beschreibung = [f"{menge}x {einheit}" for einheit, menge in kombi.items()]
                        self.tab_config_display.insert(tk.END, ", ".join(beschreibung))
        except Exception as e:
            print(f"Fehler beim Laden des Verlaufs: {e}")

    def speichere_tabverlauf(self):
        try:
            with open(self.VERLAUF_DATEI, "w", encoding="utf-8") as f:
                json.dump(self.tabgroessen_liste, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern des Verlaufs: {e}")

    def verlauf_loeschen(self):
        if os.path.exists(self.VERLAUF_DATEI):
            os.remove(self.VERLAUF_DATEI)
        self.tab_config_display.delete(0, tk.END)
        self.tabgroessen_liste.clear()

    def _parse_dt_mit_sekunden(self, s: str):
        s = (s or "").strip()
        if not s:
            return None
        return datetime.strptime(s, "%d.%m.%Y %H:%M:%S")


    def _format_dt_mit_sekunden(self, dt: datetime) -> str:
        return dt.strftime("%d.%m.%Y %H:%M:%S")


    def _zeitfenster_tree_refresh(self):
        if not self.zeitfenster_tree:
            return

        for iid in self.zeitfenster_tree.get_children():
            self.zeitfenster_tree.delete(iid)

        # iids als Index -> Entfernen ist einfach und stabil, weil wir nach jeder Änderung neu aufbauen
        for idx, (von_dt, bis_dt) in enumerate(self.zeitfenster_liste):
            self.zeitfenster_tree.insert(
                "", "end",
                iid=str(idx),
                values=(self._format_dt_mit_sekunden(von_dt), self._format_dt_mit_sekunden(bis_dt))
            )


    def zeitfenster_hinzufuegen(self):
        try:
            von_dt = self._parse_dt_mit_sekunden(self.from_entry.get())
            bis_dt = self._parse_dt_mit_sekunden(self.to_entry.get())
        except ValueError:
            messagebox.showerror("Zeitfenster Fehler", "Ungültiges Datum/Zeit-Format. Erwartet: TT.MM.JJJJ HH:MM:SS")
            return

        if not von_dt or not bis_dt:
            messagebox.showerror("Zeitfenster Fehler", "Bitte sowohl 'Von' als auch 'Bis' setzen.")
            return

        if bis_dt <= von_dt:
            messagebox.showerror("Zeitfenster Fehler", "Das 'Bis'-Datum muss nach dem 'Von'-Datum liegen.")
            return

        # optional: Duplikate verhindern
        if (von_dt, bis_dt) in self.zeitfenster_liste:
            messagebox.showinfo("Hinweis", "Dieses Zeitfenster ist bereits vorhanden.")
            return

        self.zeitfenster_liste.append((von_dt, bis_dt))
        self.zeitfenster_liste.sort(key=lambda x: x[0])

        self._zeitfenster_tree_refresh()

        # optional: Eingabefelder leeren
        self.from_entry.delete(0, tk.END)
        self.to_entry.delete(0, tk.END)


    def zeitfenster_entfernen(self):
        if not self.zeitfenster_tree:
            return

        sel = self.zeitfenster_tree.selection()
        if not sel:
            messagebox.showinfo("Hinweis", "Bitte ein Zeitfenster in der Liste auswählen.")
            return

        try:
            idx = int(sel[0])
        except ValueError:
            return

        if 0 <= idx < len(self.zeitfenster_liste):
            self.zeitfenster_liste.pop(idx)
            self._zeitfenster_tree_refresh()


    def zeitfenster_alle_loeschen(self):
        self.zeitfenster_liste.clear()
        self._zeitfenster_tree_refresh()


    def berechne_tabs(self):
        try:
            welt_id = self.welt_id_entry.get().strip()
            if not welt_id.isdigit():
                print("Ungültige Welt-ID")
                return

            self.welt_id = welt_id
            self.lade_geschwindigkeiten(welt_id)

            sos_text = self.text_fields["SOS Anfrage"].get("1.0", "end").strip()
            truppen_text = self.text_fields["Eigene Truppen"].get("1.0", "end").strip()

            angriffe = SosParser.parse(sos_text)
            eigene_dörfer = EigeneTruppenParser.parse(truppen_text)

            supports_text = self.text_fields["Unterstützungen"].get("1.0", "end").strip()

            try:
                support_filter_seconds = int(self.support_filter_seconds_entry.get().strip())
                if support_filter_seconds < 0:
                    support_filter_seconds = 0
            except Exception:
                support_filter_seconds = 0

            supports = SupportParser.parse(supports_text) if supports_text else []

            # Filter anwenden
            angriffe = self._filter_angriffe_mit_supports(angriffe, supports, support_filter_seconds)

            # Zeitfenster (immer als Liste; wenn leer -> keine Einschränkung)
            tz = pytz.timezone("Europe/Berlin")

            zeitfenster_liste_tz = []
            for von_dt, bis_dt in getattr(self, "zeitfenster_liste", []):
                # GUI speichert naive datetime; hier auf Europe/Berlin lokalisieren
                von_dt_tz = tz.localize(von_dt) if von_dt and von_dt.tzinfo is None else von_dt
                bis_dt_tz = tz.localize(bis_dt) if bis_dt and bis_dt.tzinfo is None else bis_dt

                if not von_dt_tz or not bis_dt_tz:
                    continue
                if bis_dt_tz < von_dt_tz:
                    messagebox.showerror("Zeitfenster Fehler", "Ein Zeitfenster hat 'Bis' vor 'Von'.")
                    return

                zeitfenster_liste_tz.append((von_dt_tz, bis_dt_tz))


            try:
                boost_val = int(self.boost_entry.get().strip())
                if 0 <= boost_val <= 100:
                    self.boost_level = 1 + (boost_val / 100)
                else:
                    self.boost_level = 1.0
                    print("Boost (%): Bitte Wert zwischen 0 und 100 eingeben.")
                    messagebox.showerror("Fehler", "LZ-Multiplikator (%): Bitte Wert zwischen 0 und 100 eingeben.")
            except ValueError:
                self.boost_level = 1.0
                print("Boost (%): Ungültiger Wert, Standardwert 0% verwendet.")

            self.matches = TabMatching.finde_tabs(
                angriffe=angriffe,
                eigene_dörfer=eigene_dörfer,
                tabgroessen_liste=self.tabgroessen_liste,
                welt_speed=self.welt_speed,
                einheiten_speed=self.einheiten_speed,
                zeitfenster_liste=zeitfenster_liste_tz,
                boost_level=self.boost_level
            )

            print(f"{len(self.matches)} Tabs gefunden und bereit zum Export")

            if self.export_button:
                self.export_button.config(state="normal" if self.matches else "disabled")


        except Exception as e:
            print(f"Fehler bei der Tabberechnung: {e}")


    def _filter_angriffe_mit_supports(self, angriffe, supports, nach_sekunden: int):
            """
            Entfernt Angriffe, wenn es eine Unterstützung mit gleicher Ziel-Koord gibt,
            deren Ankunftszeit im Intervall [angriff_ankunft, angriff_ankunft + nach_sekunden] liegt.
            """
            if not angriffe or not supports:
                return angriffe

            if nach_sekunden < 0:
                nach_sekunden = 0

            # Map: ziel_koord -> sortierte Liste von Ankunftszeiten (datetime)
            support_map = {}
            for s in supports:
                support_map.setdefault(s.ziel_koord, []).append(s.ankunftszeit)
            for k in support_map:
                support_map[k].sort()

            delta = timedelta(seconds=nach_sekunden)
            gefiltert = []

            for a in angriffe:
                lst = support_map.get(a.ziel_koord)
                if not lst:
                    gefiltert.append(a)
                    continue

                start = a.ankunftszeit
                end = a.ankunftszeit + delta

                i = bisect_left(lst, start)
                if i < len(lst) and lst[i] <= end:
                    # Support vorhanden -> Angriff rausfiltern
                    continue

                gefiltert.append(a)

            return gefiltert        

    def lade_config(self):
        try:
            if os.path.exists(self.CONFIG_DATEI):
                with open(self.CONFIG_DATEI, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.dsu_api_key = (cfg.get("dsu_api_key") or "")
                self.archer_enabled = bool(cfg.get("archer_enabled", False))
        except Exception as e:
            print(f"Fehler beim Laden der Config: {e}")

    def speichere_config(self):
        try:
            cfg = {
                "dsu_api_key": self.dsu_api_key,
                "archer_enabled": self.archer_enabled,
            }
            with open(self.CONFIG_DATEI, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")


    def lade_geschwindigkeiten(self, welt_id):
        url = f"https://de{welt_id}.die-staemme.de/page/settings"
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            welt_row = soup.find("td", string="Spielgeschwindigkeit")
            einheit_row = soup.find("td", string="Einheitengeschwindigkeit")

            if not welt_row or not einheit_row:
                raise ValueError("Konnte Geschwindigkeitsdaten nicht finden.")

            welt_speed = welt_row.find_next_sibling("td").text.strip()
            einheit_speed = einheit_row.find_next_sibling("td").text.strip()

            print(f"[INFO] Weltgeschwindigkeit: {welt_speed}, Einheitengeschwindigkeit: {einheit_speed}")

            self.welt_speed = float(welt_speed)
            self.einheiten_speed = float(einheit_speed)
        except Exception as e:
            print(f"Fehler beim Laden der Geschwindigkeiten: {e}")


    def datum_popup(self, title, entry_widget):
        popup = tk.Toplevel(self.tk_root)
        popup.title(title)
        popup.geometry("280x250")
        popup.resizable(False, False)

        is_bis = "bis" in title.lower()
        default_time = datetime.now() + timedelta(hours=1) if is_bis else datetime.now()

        def übernehmen():
            try:
                dt = datetime(
                    int(year.get()), int(month.get()), int(day.get()),
                    int(hour.get()), int(minute.get()), int(second.get())
                )
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, dt.strftime("%d.%m.%Y %H:%M:%S"))
                popup.destroy()
            except:
                print("Datum ungültig")

        def jetzt():
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
            popup.destroy()

        def plus_min():
            try:
                minuten = int(plus.get())
                dt = datetime.now() + timedelta(minutes=minuten)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, dt.strftime("%d.%m.%Y %H:%M:%S"))
                popup.destroy()
            except:
                print("Minuten ungültig")

        container = ttk.Frame(popup)
        container.pack(expand=True)

        ttk.Label(container, text="Datum & Uhrzeit wählen", font=("Segoe UI", 10, "bold")).pack(pady=(10, 10))

        grid = ttk.Frame(container)
        grid.pack()

        year = ttk.Combobox(grid, values=list(range(2024, 2031)), width=5)
        year.set(default_time.year)
        year.grid(row=0, column=0)

        month = ttk.Combobox(grid, values=list(range(1, 13)), width=3)
        month.set(default_time.month)
        month.grid(row=0, column=1)

        day = ttk.Combobox(grid, values=list(range(1, 32)), width=3)
        day.set(default_time.day)
        day.grid(row=0, column=2)

        hour = ttk.Combobox(grid, values=list(range(0, 24)), width=3)
        hour.set(default_time.hour)
        hour.grid(row=1, column=0)

        minute = ttk.Combobox(grid, values=list(range(0, 60)), width=3)
        minute.set(default_time.minute)
        minute.grid(row=1, column=1)

        second = ttk.Combobox(grid, values=list(range(0, 60)), width=3)
        second.set(default_time.second)
        second.grid(row=1, column=2)

        if not is_bis:
            ttk.Button(container, text="Jetzt", command=jetzt).pack(pady=(5, 0))

        plus_frame = ttk.Frame(container)
        plus_frame.pack(pady=(5, 5))
        plus = ttk.Entry(plus_frame, width=5)
        plus.insert(0, "60")
        plus.grid(row=0, column=0)
        ttk.Button(plus_frame, text="+ Min", command=plus_min).grid(row=0, column=1, padx=5)

        ttk.Button(container, text="Übernehmen", command=übernehmen).pack(pady=(5, 10))

    def exportiere(self):
        try:
            export_text = TabMatching.export_dsultimate(self.matches, self.welt_id_entry.get().strip())
            pfad = filedialog.asksaveasfilename(
                defaultextension=".txt", filetypes=[("Textdateien", "*.txt")], title="Speichern unter"
            )
            if pfad:
                with open(pfad, "w", encoding="utf-8") as f:
                    f.write(export_text)
                print(f"Export erfolgreich: {pfad}")
        except Exception as e:
            print(f"Export fehlgeschlagen: {e}")

# GUI starten
if __name__ == "__main__":
    root = tk.Tk()
    app = StammGUI(root)
    root.iconbitmap(resource_path("support.ico")) 
    root.mainloop()


