#!/usr/bin/env python3
"""
main.py

Startet die Chat-Client-Anwendung mit:
1) einer Benutzeroberfläche (UI)
2) einem Discovery-Prozess für lokale Peer-Erkennung
"""

import toml
import sys
import signal
from multiprocessing import Process, Queue

from efe_chat_ui import ChatClientUI
from netzwerk import send_join_broadcast, send_leave_broadcast
from discovery import discovery_loop

def main():
    # 1. Zentrale Konfiguration laden
    config    = toml.load("config.toml")
    handle    = config.get("handle",    "User")
    port      = config.get("port",      5000)
    whoisport = config.get("whoisport", 4000)

    # 2. UI-Instanz erzeugen
    ui = ChatClientUI(config_path="config.toml")

    # 3. IPC-Queues (für zukünftige Erweiterungen)
    ui_to_net = Queue()
    net_to_ui = Queue()

    # 4. JOIN-Broadcast senden (Discovery wird informiert)
    send_join_broadcast(handle, port, whoisport)

    # 5. Sub-Prozesse anlegen
    processes = [
        Process(
            target=ui.run,
            args=(ui_to_net, net_to_ui),
            name="UI-Prozess"
        ),
        Process(
            target=discovery_loop,
            args=(whoisport, ui_to_net),
            name="Discovery-Prozess"
        )
    ]

    # 6. Signal-Handler für sauberes Beenden
    def on_exit(signum, frame):
        # LEAVE-Broadcast senden
        send_leave_broadcast(handle, whoisport)
        # Alle Sub-Prozesse terminieren
        for p in processes:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT,  on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    # 7. Prozesse starten
    for proc in processes:
        print(f"Starte {proc.name} …")
        proc.start()

    # 8. Auf Ende warten
    for proc in processes:
        proc.join()

if __name__ == "__main__":
    main()
