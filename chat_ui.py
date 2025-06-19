import toml
import os
import sys
import queue
from multiprocessing import Queue
from netzwerk import send_msg

class ChatClientUI:
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

        # Initiale Handle-Eingabe immer
        new_handle = input("Bitte gib deinen Handle ein: ").strip()
        if not new_handle:
            print("Kein Handle eingegeben, verwende 'User'.")
            new_handle = "User"
        self.config["handle"] = new_handle
        self.save_config(self.config)

        self.peers = {}  # Peer-Liste: handle -> (ip, port)

    def save_config(self, config):
        with open(self.CONFIG_FILE, "w") as f:
            toml.dump(config, f)

    def change_config(self):
        print("\n--- Konfiguration ändern ---")
        for key in ("port", "autoreply", "imagepath"):
            current = self.config.get(key)
            new = input(f"{key} (aktuell: {current}): ")
            if new.strip():
                self.config[key] = int(new) if key == "port" else new
        self.save_config(self.config)
        print("Konfiguration gespeichert.\n")

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

        print(f"Willkommen, {handle}! (Chat-Port: {port})")
        print("Gib '/help' für Befehle ein. Nachrichten ohne '/' werden broadcastet.")

        while True:
            # Eingehende Nachrichten und Events anzeigen
            try:
                while True:
                    msg = net_to_ui.get_nowait()
                    print(msg)
            except queue.Empty:
                pass

            # Benutzereingabe
            text = input("> ").strip()
            if not text:
                continue

            if text.startswith("/"):
                parts = text.split(maxsplit=2)
                cmd = parts[0]

                if cmd == "/help":
                    print("Befehle:\n /who     - Teilnehmerliste abfragen\n /msg <Handle> <Nachricht> - Direktnachricht senden\n /config  - Konfiguration ändern\n /quit    - Chat beenden")

                elif cmd == "/who":
                    ui_to_net.put("WHO")

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
                # Broadcast-Nachricht
                ui_to_net.put(text)

if __name__ == "__main__":
    ui = ChatClientUI()
    ui.run(Queue(), Queue())