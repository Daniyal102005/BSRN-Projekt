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
from netzwerk import send_msg, send_who_broadcast

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
            "handle": "User",
            "port": 5000,
            "whoisport": 4000,
            "autoreply": "Ich bin gerade nicht da.",
            "imagepath": "./images"
        }
        self.config = self.load_config()
        self.peers = {}  # Peer-Liste: handle -> (ip, port)

    ## \brief Lädt die Konfiguration aus einer TOML-Datei.
    def load_config(self):
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config(self.DEFAULT_CONFIG)
        with open(self.CONFIG_FILE, "r") as f:
            return toml.load(f)

    ## \brief Speichert die Konfiguration in eine TOML-Datei.
    def save_config(self, config):
        with open(self.CONFIG_FILE, "w") as f:
            toml.dump(config, f)

    ## \brief Ändert die Konfiguration über Benutzereingabe (außer whoisport).
    def change_config(self):
        print("\n--- Konfiguration ändern ---")
        for key in ("handle", "port", "autoreply", "imagepath"):
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
         - Befehle: /help, /who, /msg <Handle> <Text>, /config, /quit
         - Nachrichten ohne '/' werden als Broadcast via ui_to_net gesendet
        """
        handle = self.config["handle"]
        port = self.config["port"]
        whoisport = self.config["whoisport"]
        autoreply = self.config.get("autoreply")

        print(f"Willkommen, {handle}! (Chat-Port: {port})")
        print("Gib '/help' für Befehle ein. Nachrichten ohne '/' werden broadcastet.")

        while True:
            try:
                while True:
                    msg = net_to_ui.get_nowait()
                    if msg.startswith("[WHO-REPLY]"):
                        entries = msg.split(' ',1)[1].split(';')
                        self.peers.clear()
                        for entry in entries:
                            h, ip, p = entry.split()
                            self.peers[h] = (ip, int(p))
                        print("Peers im Netzwerk:", ", ".join(self.peers.keys()))
                    else:
                        print(msg)
            except queue.Empty:
                pass

            text = input("> ").strip()
            if not text:
                continue

            if text.startswith("/"):
                parts = text.split(maxsplit=2)
                cmd = parts[0]

                if cmd == "/help":
                    print("Befehle:\n /who     - Teilnehmerliste abfragen\n /msg <Handle> <Nachricht> - Direktnachricht senden\n /config  - Konfiguration ändern\n /quit    - Chat beenden")

                elif cmd == "/who":
                    send_who_broadcast(whoisport)

                elif cmd == "/msg":
                    if len(parts) < 3:
                        print("Nutzung: /msg <Handle> <Nachricht>")
                    else:
                        _, target, message = parts
                        if target not in self.peers:
                            print(f"Unbekannter Peer: {target}")
                        else:
                            ip, p = self.peers[target]
                            send_msg(handle, message, ip, p)
                            print(f"[Du -> {target}] {message}")

                elif cmd == "/config":
                    self.change_config()

                elif cmd == "/quit":
                    print("Beende Chat-Client…")
                    sys.exit(0)

                else:
                    print(f"Unbekannter Befehl: {cmd}. '/help' für Übersicht.")
            else:
                ui_to_net.put(text)

## \brief Startpunkt bei direktem Ausführen des Skripts
if __name__ == "__main__":
    ui = ChatClientUI()
    ui.run(Queue(), Queue())
