##
# @file discovery.py
# @brief Discovery-Dienst für SLCP-Protokoll (vereinfachte Broadcast-Erkennung).
#
# @details Dieses Modul implementiert einen UDP-basierten Discovery-Dienst für Chat-Teilnehmer.
# Es verarbeitet JOIN-, LEAVE- und WHO-Anfragen und antwortet mit KNOWNUSERS-Nachrichten.
# Eine automatische Bereinigung entfernt inaktive Teilnehmer nach Zeitablauf.
#
# @author Aset Sejtikov
# @date 22.06.2024

import socket
import time
import threading
from multiprocessing import Queue

##
# @brief Startet den Discovery-Dienst zur Peer-Erkennung.
#
# @details
# - Lauscht auf JOIN, LEAVE und WHO-Befehle
# - Antwortet auf WHO mit "KNOWNUSERS"
# - Verwaltet eine Teilnehmerliste mit Zeitstempel
# - Startet einen Cleanup-Thread für inaktive Nutzer
#
# @param whoisport Port für Discovery-Kommunikation (standardmäßig 4000)
# @param ui_to_net Queue zur (optionalen) Kommunikation mit der Benutzeroberfläche

def discovery_loop(whoisport: int, ui_to_net: Queue):
    teilnehmer = {}  # Dictionary für Teilnehmer: handle -> (IP, Port, letzter_heartbeat)
    PORT = whoisport
    MaxBytes = 1024

    print(f"[DISCOVERY] Starte Discovery-Dienst auf Port {PORT}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.bind(('', PORT))
        print(f"[DISCOVERY] Discovery-Dienst läuft auf Port {PORT}")

        # Cleanup-Thread starten
        cleanup_thread = threading.Thread(target=cleanup_old_participants, args=(teilnehmer,), daemon=True)
        cleanup_thread.start()

        while True:
            try:
                daten, addresse = sock.recvfrom(MaxBytes)
                nachricht = daten.decode("utf-8").strip()
                sender_ip = addresse[0]

                print(f"[DISCOVERY] Empfangen von {sender_ip}: {nachricht}")

                teile = nachricht.split()
                if not teile:
                    continue

                befehl = teile[0].upper()

                ## Verarbeitung der JOIN-Nachricht
                if befehl == "JOIN" and len(teile) >= 3:
                    handle = teile[1]
                    try:
                        client_port = int(teile[2])
                        teilnehmer[handle] = (sender_ip, client_port, time.time())
                        print(f"[DISCOVERY] Teilnehmer registriert: {handle} @ {sender_ip}:{client_port}")

                        antwort = f"JOIN_ACK {handle}"
                        sock.sendto(antwort.encode("utf-8"), addresse)

                    except ValueError:
                        print(f"[DISCOVERY] Ungültiger Port in JOIN: {nachricht}")

                ## Verarbeitung der LEAVE-Nachricht
                elif befehl == "LEAVE" and len(teile) >= 2:
                    handle = teile[1]
                    if handle in teilnehmer:
                        del teilnehmer[handle]
                        print(f"[DISCOVERY] Teilnehmer abgemeldet: {handle}")

                        antwort = f"LEAVE_ACK {handle}"
                        sock.sendto(antwort.encode("utf-8"), addresse)
                    else:
                        print(f"[DISCOVERY] Unbekannter Teilnehmer bei LEAVE: {handle}")

                ## Verarbeitung der WHO-Nachricht
                elif befehl == "WHO":
                    print(f"[DISCOVERY] WHO-Anfrage von {sender_ip}, bekannte Teilnehmer: {len(teilnehmer)}")
                    if teilnehmer:
                        teilnehmer_liste = [f"{h} {ip} {p}" for h, (ip, p, _) in teilnehmer.items()]
                        antwort = "KNOWNUSERS " + ",".join(teilnehmer_liste)
                    else:
                        antwort = "KNOWNUSERS"

                    print(f"[DISCOVERY] Sende Antwort: {antwort}")
                    sock.sendto(antwort.encode("utf-8"), addresse)

                ## Verarbeitung unbekannter Befehle
                else:
                    print(f"[DISCOVERY] Unbekannter Befehl: {nachricht}")
                    antwort = "ERROR: Unbekannter Befehl"
                    sock.sendto(antwort.encode("utf-8"), addresse)

            except UnicodeDecodeError:
                print("[DISCOVERY] Fehler beim Dekodieren der Nachricht")
            except Exception as e:
                print(f"[DISCOVERY] Fehler beim Verarbeiten der Nachricht: {e}")

    except Exception as e:
        print(f"[DISCOVERY] Kritischer Fehler: {e}")
    finally:
        sock.close()
        print("[DISCOVERY] Discovery-Dienst beendet")

##
# @brief Entfernt inaktive Teilnehmer aus dem Teilnehmer-Dictionary.
#
# @details
# Teilnehmer gelten als inaktiv, wenn seit ihrer letzten Aktivitaet mehr als `max_age` Sekunden vergangen sind.
# Diese Funktion läuft im Hintergrund-Thread und prüft alle 60 Sekunden.
#
# @param teilnehmer Dictionary mit aktuellen Teilnehmern (Handle -> (IP, Port, Timestamp))
# @param max_age Maximale Inaktivzeit in Sekunden (Standard: 300 Sekunden)

def cleanup_old_participants(teilnehmer: dict, max_age: int = 300):
    while True:
        try:
            current_time = time.time()
            expired_handles = [h for h, (_, _, last) in teilnehmer.items() if current_time - last > max_age]

            for handle in expired_handles:
                del teilnehmer[handle]
                print(f"[DISCOVERY] Teilnehmer wegen Timeout entfernt: {handle}")

            time.sleep(60)

        except Exception as e:
            print(f"[DISCOVERY] Cleanup-Fehler: {e}")
            time.sleep(60)