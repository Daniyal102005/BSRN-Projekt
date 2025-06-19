import toml
import sys
import signal
from multiprocessing import Process, Queue

from efe_chat_ui import ChatClientUI
from network import network_loop, send_leave_broadcast
from discovery import discovery_loop


def main():
    # 1. Zentrale Konfiguration laden
    config    = toml.load("config.toml")
    handle    = config.get("handle",    "User")
    port      = config.get("port",      5000)
    whoisport = config.get("whoisport", 4000)

    # 2. UI-Instanz erzeugen
    ui = ChatClientUI(config_path="config.toml")

    # 3. IPC-Queues für UI ↔ Netzwerk
    ui_to_net = Queue()
    net_to_ui = Queue()

    # 4. Sub-Prozesse definieren
    processes = [
        Process(
            target=ui.run,
            args=(ui_to_net, net_to_ui),
            name="UI-Prozess"
        ),
        Process(
            target=network_loop,
            args=(ui_to_net, net_to_ui, handle, port, whoisport),
            name="Netzwerk-Prozess"
        ),
        Process(
            target=discovery_loop,
            args=(whoisport, ui_to_net),
            name="Discovery-Prozess"
        )
    ]

    # 5. Signal-Handler für sauberes Beenden
    def on_exit(signum, frame):
        # LEAVE-Broadcast senden
        send_leave_broadcast(handle, whoisport)
        # Alle Sub-Prozesse terminieren
        for proc in processes:
            proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT,  on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    # 6. Prozesse starten
    for proc in processes:
        print(f"Starte {proc.name} …")
        proc.start()

    # 7. Auf Ende warten
    for proc in processes:
        proc.join()


if __name__ == "__main__":
    main()