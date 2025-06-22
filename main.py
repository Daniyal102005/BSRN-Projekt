import toml 
import sys
import signal
import time
import threading
from multiprocessing import Process, Queue

from chat_ui import ChatClientUI
from netzwerk import send_join_broadcast, send_leave_broadcast, network_loop
from discovery import discovery_loop


#/**
# * @brief Haupteinstiegspunkt des Chat-Programms
# * @details Initialisiert Konfiguration, UI und Netzwerk-/Discovery-Prozesse
# */
def main():
    #/**
    # * @brief Zentrale Konfiguration laden
    # * @details Lädt Einstellungen aus der Datei "config.toml" und setzt Standardwerte,
    # *          falls bestimmte Werte nicht definiert sind.
    # */
    config    = toml.load("config.toml")
    handle    = config.get("handle",    "User")
    port      = config.get("port",      5000)
    whoisport = config.get("whoisport", 4000)

    #/**
    # * @brief Startmeldung ausgeben
    # * @details Gibt eine Information aus, welcher Benutzerhandle und Port verwendet werden.
    # */
    print(f"[MAIN] Starte Chat-Client für '{handle}' auf Port {port}")

    #/**
    # * @brief UI-Instanz erzeugen
    # * @details Erstellt eine ChatClientUI-Instanz mit dem gegebenen Konfigurationspfad.
    # */
    ui = ChatClientUI(config_path="config.toml")

    #/**
    # * @brief IPC-Queues anlegen
    # * @details Erstellt zwei multiprocessing.Queue-Objekte für die Kommunikation
    # *          zwischen UI und Netzwerk-Prozess.
    # */
    ui_to_net = Queue()
    net_to_ui = Queue()

    #/**
    # * @brief Netzwerk- und Discovery-Prozesse erstellen
    # * @details Definiert zwei separate Prozesse: einen für den Netzwerk-Loop
    # *          und einen für die Discovery-Funktionalität.
    # */
    processes = [
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

    #/**
    # * @brief Signal-Handler für sauberes Beenden
    # * @details Registriert Funktionen, um auf SIGINT und SIGTERM zu reagieren.
    # */
    def on_exit(signum, frame):
        print(f"\n[MAIN] Empfangen Signal {signum}, beende Programm...")
        cleanup_and_exit()

    #/**
    # * @brief Aufräumen und Beenden aller Prozesse
    # * @details Sendet LEAVE-Broadcast, terminiert Subprozesse und beendet das Skript.
    # */
    def cleanup_and_exit():
        #/**
        # * @brief LEAVE-Broadcast senden
        # * @details Sendet eine Abmeldung an alle Teilnehmer über den Whois-Port
        # *          und wartet kurz, damit das Paket übertragen wird.
        # */
        try:
            send_leave_broadcast(handle, whoisport)
            time.sleep(0.5)  # Kurz warten damit LEAVE gesendet wird
        except Exception as e:
            print(f"[MAIN] Fehler beim Senden von LEAVE: {e}")
        
        #/**
        # * @brief Subprozesse terminieren
        # * @details Versucht, alle gestarteten Prozesse zuerst ordentlich zu beenden,
        # *          anschließend ggf. zwangsweise zu killen.
        # */
        for proc in processes:
            if proc.is_alive():
                print(f"[MAIN] Beende {proc.name}...")
                proc.terminate()
        
        # Warten bis alle beendet sind
        for proc in processes:
            proc.join(timeout=2)
            if proc.is_alive():
                print(f"[MAIN] Forciere Beendigung von {proc.name}")
                proc.kill()
        
        print("[MAIN] Alle Prozesse beendet.")
        sys.exit(0)

    #/**
    # * @brief Registrierung der Signal-Handler
    # * @details Verknüpft SIGINT und SIGTERM mit der on_exit-Funktion.
    # */
    signal.signal(signal.SIGINT,  on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    #/**
    # * @brief Prozesse starten
    # * @details Startet zuerst den Discovery-Prozess, wartet auf Bereitstellung,
    # *          und anschließend den Netzwerk-Prozess.
    # */
    try:
        # Discovery-Prozess ZUERST starten (vor JOIN!)
        discovery_proc = processes[1]  # Discovery ist der zweite Prozess
        network_proc = processes[0]    # Netzwerk ist der erste Prozess
        
        print(f"[MAIN] Starte {discovery_proc.name} (zuerst)...")
        discovery_proc.start()
        time.sleep(1.0)  # Warten bis Discovery bereit ist
        print(f"[MAIN] Discovery bereit, starte {network_proc.name}...")
        network_proc.start()
        time.sleep(0.2)

        print("[MAIN] Hintergrund-Prozesse gestartet.")
        print(f"[MAIN] Starte UI im Hauptprozess...")
        
        #/**
        # * @brief UI im Hauptprozess ausführen
        # * @details Führt die Benutzeroberfläche aus und behandelt Interrupts und Fehler.
        # */
        try:
            ui.run(ui_to_net, net_to_ui)
        except KeyboardInterrupt:
            print("\n[MAIN] Keyboard Interrupt im UI")
        except Exception as e:
            print(f"[MAIN] UI-Fehler: {e}")

    except KeyboardInterrupt:
        print("\n[MAIN] Keyboard Interrupt empfangen")
    except Exception as e:
        print(f"[MAIN] Unerwarteter Fehler: {e}")
    finally:
        cleanup_and_exit()


#/**
# * @brief Script-Ausführung
# * @details Ruft main() auf, wenn das Modul als Hauptprogramm gestartet wird.
# */
if __name__ == "__main__":
    main()