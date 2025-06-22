"""
@file chat_ui.py
@brief Kommandozeilen-Oberfläche und Logik für den Chat-Client.

Dieses Modul verwaltet die Benutzereingaben, Konfigurationen,
Nachrichtenaustausch und Discovery-Kommunikation via Queue.
"""

import toml
import os
import sys
import queue
from multiprocessing import Queue
from netzwerk import send_msg, send_img

## \class ChatClientUI
#  \brief Diese Klasse stellt die textbasierte Benutzeroberfläche und Netzwerklogik bereit.
#  Sie verarbeitet Eingaben, lädt und speichert Konfigurationen,
#  und kommuniziert mit dem Netzwerkprozess über Queues.
class ChatClientUI:
    ## \brief Initialisiert das UI und lädt Konfiguration.
    #  \param config_path Pfad zur TOML-Konfigurationsdatei.
    def __init__(self, config_path="config.toml"):
        self.CONFIG_FILE = config_path
        self.DEFAULT_CONFIG = {
            "handle": None,
            "port": 5000,
            "whoisport": 4000,
            "autoreply": "Ich bin gerade nicht da.",
            "imagepath": "./images"
        }
        # Config laden oder erzeugen
        if not os.path.exists(self.CONFIG_FILE):
            self.config = dict(self.DEFAULT_CONFIG)
            self.save_config(self.config)
        else:
            with open(self.CONFIG_FILE, "r") as f:
                self.config = toml.load(f)

        # Handle-Eingabe bei jedem Start (für eindeutige Namen im Netzwerk)
        old_handle = self.config.get("handle", "")
        prompt = f"Bitte gib deinen Handle ein (zuletzt: {old_handle}): " if old_handle else "Bitte gib deinen Handle ein: "
        
        new_handle = input(prompt).strip()
        if not new_handle:
            if old_handle:
                new_handle = old_handle
                print(f"Verwende vorherigen Handle: {old_handle}")
            else:
                new_handle = "User"
                print("Kein Handle eingegeben, verwende 'User'.")
        
        self.config["handle"] = new_handle
        self.save_config(self.config)

        self.peers = {}  # Peer-Liste: handle -> (ip, port)

    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config(self.DEFAULT_CONFIG)
        with open(self.CONFIG_FILE, "r") as f:
            return toml.load(f)

    def save_config(self, config):
        with open(self.CONFIG_FILE, "w") as f:
            toml.dump(config, f)

    ## \brief Ändert die Konfiguration über Benutzereingabe (außer whoisport).
    def change_config(self):
        print("\n--- Konfiguration ändern ---")
        for key in ("port", "autoreply", "imagepath"):
            current = self.config.get(key)
            new = input(f"{key} (aktuell: {current}): ")
            if new.strip():
                self.config[key] = int(new) if key == "port" else new
        self.save_config(self.config)
        print("Konfiguration gespeichert.\n")

    ## \brief Startet das textbasierte UI: verarbeitet alle Eingaben und zeigt Netzwerknachrichten an.
    #  \param ui_to_net Queue zum Senden von Nachrichten.
    #  \param net_to_ui Queue zum Empfangen von Netzwerkereignissen.
    def run(self, ui_to_net: Queue, net_to_ui: Queue):
        """
        Startet die Chat-Schleife:
         - Anzeige eingehender Nachrichten und Discovery-Events aus net_to_ui
         - Befehle: /help, /who, /msg <Handle> <Text>, /img <Handle> <Bildpfad>, /config, /quit
         - Nachrichten ohne '/' werden als Broadcast via ui_to_net gesendet
        """
        handle = self.config["handle"]
        port = self.config["port"]
        whoisport = self.config["whoisport"]

        print(f"Willkommen, {handle}! (Chat-Port: {port})")
        print("Gib '/help' für Befehle ein. Nachrichten ohne '/' werden broadcastet.")

        while True:
            # Anzeigen aller eingehenden Nachrichten und Events
            try:
                while True:
                    msg = net_to_ui.get_nowait()
                    
                    # Discovery-Event: Fülle Peer-Liste bei WHO-Reply
                    if msg.startswith("[WHO-REPLY]"):
                        reply_content = msg[11:].strip()  # "[WHO-REPLY] " entfernen
                        
                        if reply_content and not reply_content.startswith("Keine") and not reply_content.startswith("Fehler"):
                            # Format: "Alice 192.168.1.5 5000;Bob 192.168.1.6 5001"
                            self.peers.clear()
                            
                            for entry in reply_content.split(';'):
                                entry = entry.strip()
                                if entry:
                                    parts = entry.split()
                                    if len(parts) >= 3:
                                        h, ip, p = parts[0], parts[1], parts[2]
                                        try:
                                            self.peers[h] = (ip, int(p))
                                        except ValueError:
                                            print(f"[WARNUNG] Ungültiger Port für {h}: {p}")
                            
                            if self.peers:
                                peer_names = list(self.peers.keys())
                                print(f"Teilnehmer im Netzwerk ({len(peer_names)}): {', '.join(peer_names)}")
                            else:
                                print("Keine anderen Teilnehmer im Netzwerk gefunden.")
                        else:
                            print("Keine anderen Teilnehmer im Netzwerk gefunden.")
                    else:
                        # Normale Nachricht anzeigen
                        print(msg)
                        
            except queue.Empty:
                pass

            # Eingabe
            text = input("> ").strip()
            if not text:
                continue

            if text.startswith("/"):
                parts = text.split(maxsplit=2)
                cmd = parts[0]

                if cmd == "/help":
                    print("Befehle:")
                    print(" /who     - Teilnehmerliste abfragen")
                    print(" /msg <Handle> <Nachricht> - Direktnachricht senden")
                    print(" /img <Handle> <Bildpfad>  - Bild an Benutzer senden")
                    print(" /config  - Konfiguration ändern")
                    print(" /quit    - Chat beenden")

                elif cmd == "/who":
                    # Discovery Anfrage über Queue
                    print("Suche nach anderen Teilnehmern...")
                    ui_to_net.put("WHO")

                elif cmd == "/msg":
                    if len(parts) < 3:
                        print("Nutzung: /msg <Handle> <Nachricht>")
                    else:
                        _, target, message = parts
                        if target not in self.peers:
                            print(f"Unbekannter Peer: {target}. Verwende '/who' um verfügbare Teilnehmer zu finden.")
                        else:
                            ip, p = self.peers[target]
                            try:
                                send_msg(handle, message, ip, p)
                                print(f"[Du -> {target}] {message}")
                            except Exception as e:
                                print(f"Fehler beim Senden an {target}: {e}")

                elif cmd == "/img":
                    if len(parts) < 3:
                        print("Nutzung: /img <Handle> <Bildpfad>")
                        print("Beispiel: /img Alice ./bild.jpg")
                    else:
                        _, target, image_path = parts
                        if target not in self.peers:
                            print(f"Unbekannter Peer: {target}. Verwende '/who' um verfügbare Teilnehmer zu finden.")
                        else:
                            # Bildpfad validieren
                            if not os.path.exists(image_path):
                                print(f"Bilddatei nicht gefunden: {image_path}")
                            else:
                                ip, p = self.peers[target]
                                try:
                                    success = send_img(handle, image_path, ip, p)
                                    if success:
                                        print(f"[📷 Du -> {target}] Bild gesendet: {os.path.basename(image_path)}")
                                    else:
                                        print(f"Fehler beim Senden des Bildes an {target}")
                                except Exception as e:
                                    print(f"Fehler beim Senden des Bildes an {target}: {e}")

                elif cmd == "/config":
                    self.change_config()

                elif cmd == "/quit":
                    print("Beende Chat-Client…")
                    # Sende LEAVE-Nachricht
                    ui_to_net.put("QUIT")
                    sys.exit(0)

                else:
                    print(f"Unbekannter Befehl: {cmd}. '/help' für Übersicht.")
            else:
                # Broadcast-Nachricht an alle über Queue
                ui_to_net.put(text)

## \brief Startpunkt bei direktem Ausführen des Skripts
if __name__ == "__main__":
    ui = ChatClientUI()
    ui.run(Queue(), Queue())
