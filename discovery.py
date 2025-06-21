import socket 
import os
import sys
from multiprocessing import Queue

def discovery_loop(whoisport: int, ui_to_net: Queue):

    teilnehmer = {}  # Dictionary für Teilnehmer: handle -> (IP-Adresse, Port)
    LOCKFILE = "discovery.lock"  # Lockfile zum Schutz vor Mehrfachstart

    # Überprüfen, ob der Dienst bereits läuft
    if os.path.exists(LOCKFILE):
        print("[INFO] Discovery-Dienst läuft bereits. Beende Startversuch.")
        sys.exit()

    # Lockfile erstellen
    with open(LOCKFILE, "w") as f:
        f.write("active")

    # UDP-Socket erstellen
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Broadcast erlauben
    sock.bind(('', 4000))  # Socket auf allen Schnittstellen öffnen ('' = 0.0.0.0)

    print("Discovery-Dienst läuft auf Port", 4000)

    try:
        # Endlosschleife zur Verarbeitung eingehender Nachrichten
        while True:
            try:
                # Empfang der Daten vom Netzwerk
                daten, addresse = sock.recvfrom(1024)# 1024 Bytes Puffergröße
                nachricht = daten.decode("utf-8").strip()  # Umwandlung von Bytes zu String

                # Verarbeitung der JOIN-Nachricht: Teilnehmer beitreten lassen
                if nachricht.startswith("JOIN"):
                    _, handle, port = nachricht.split()  # handle = Benutzername, port = Client-Port
                    ip = addresse[0]  # IP-Adresse des Senders auslesen
                    teilnehmer[handle] = (ip, int(port))  # Teilnehmer speichern
                    antwort = f"JOIN {handle} {port}"
                    sock.sendto(antwort.encode("utf-8"), addresse)  # Bestätigung zurücksenden

                # Verarbeitung der LEAVE-Nachricht: Teilnehmer austragen
                elif nachricht.startswith("LEAVE"):
                    _, handle = nachricht.split()
                    if handle in teilnehmer:
                        del teilnehmer[handle]  # Teilnehmer aus Dictionary entfernen
                        antwort = f"LEAVE {handle}"
                    else:
                        antwort = f"[WARNUNG] {handle} nicht gefunden"
                    sock.sendto(antwort.encode("utf-8"), addresse)  # Bestätigung zurücksenden

                # Verarbeitung der WHO-Nachricht: Teilnehmerliste zurücksenden
                elif nachricht == "WHO":
                    antwort = "KNOWNUSERS " + ", ".join(
                        f"{handle} {ip} {port}"
                        for handle, (ip, port) in teilnehmer.items()
                    )
                    sock.sendto(antwort.encode("utf-8"), addresse)  # Teilnehmerliste senden

                # Alle anderen Nachrichten sind unbekannt
                else:
                    antwort = "ERROR: Unbekannter Befehl"
                    sock.sendto(antwort.encode("utf-8"), addresse)

            # Fehler beim Parsen (z. B. falsches Nachrichtenformat)
            except ValueError:
                antwort = "ERROR: Falsches Nachrichtenformat"
                sock.sendto(antwort.encode("utf-8"), addresse)
                print("Fehler! Falsches Nachrichtenformat!")

    except KeyboardInterrupt:
        print("\n[Beende durch Benutzer]")

    finally:
        # Lockfile entfernen beim Beenden
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
        print("[INFO] Lockfile entfernt. Discovery-Dienst beendet.")
