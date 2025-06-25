import socket 
import time
import threading
from multiprocessing import Queue

def discovery_loop(whoisport: int, ui_to_net: Queue):
    """
    Discovery-Dienst für SLCP Protokoll.
    
    Verarbeitet:
    - JOIN <handle> <port> - Registriert neuen Teilnehmer
    - LEAVE <handle> - Entfernt Teilnehmer  
    - WHO - Sendet Liste aller bekannten Teilnehmer zurück
    
    Args:
        whoisport: Port für Discovery-Kommunikation (normalerweise 4000)
        ui_to_net: Queue für Kommunikation mit UI (wird hier nicht verwendet)
    """
    
    teilnehmer = {}  # Dictionary für Teilnehmer: handle -> (IP, Port, letzter_heartbeat)
    PORT = whoisport  # Port für den Discovery-Dienst laut SLCP-Spezifikation
    MaxBytes = 1024   # Maximale Größe für empfangene Nachrichten
    
    print(f"[DISCOVERY] Starte Discovery-Dienst auf Port {PORT}")
    
    # UDP-Socket erstellen und konfigurieren
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    
    try:
        # Socket binden - auf allen Interfaces lauschen
        sock.bind(('', PORT))
        
        # Cleanup-Thread für veraltete Einträge starten
        cleanup_thread = threading.Thread(target=cleanup_old_participants, args=(teilnehmer,), daemon=True)
        cleanup_thread.start()
        
        # Hauptschleife für eingehende Nachrichten
        while True:
            try:
                # Empfang der Daten vom Netzwerk
                daten, addresse = sock.recvfrom(MaxBytes)
                nachricht = daten.decode("utf-8").strip()
                sender_ip = addresse[0]
                
                
                # Nachricht parsen und verarbeiten
                teile = nachricht.split()
                if not teile:
                    continue
                    
                befehl = teile[0].upper()
                
                if befehl == "JOIN" and len(teile) >= 3:
                    # JOIN <handle> <port>
                    handle = teile[1]
                    try:
                        client_port = int(teile[2])
                        # Teilnehmer registrieren mit aktuellem Zeitstempel
                        teilnehmer[handle] = (sender_ip, client_port, time.time())
                        print(f"[DISCOVERY] Teilnehmer registriert: {handle} @ {sender_ip}:{client_port}")
                        
                        # Bestätigung senden (optional, nicht im Protokoll spezifiziert)
                        antwort = f"JOIN_ACK {handle}"
                        sock.sendto(antwort.encode("utf-8"), addresse)
                        
                    except ValueError:
                        print(f"[DISCOVERY] Ungültiger Port in JOIN: {nachricht}")
                
                elif befehl == "LEAVE" and len(teile) >= 2:
                    # LEAVE <handle>
                    handle = teile[1]
                    if handle in teilnehmer:
                        del teilnehmer[handle]
                        print(f"[DISCOVERY] Teilnehmer abgemeldet: {handle}")
                        
                        # Bestätigung senden
                        antwort = f"LEAVE_ACK {handle}"
                        sock.sendto(antwort.encode("utf-8"), addresse)
                    else:
                        print(f"[DISCOVERY] Unbekannter Teilnehmer bei LEAVE: {handle}")
                
                elif befehl == "WHO":
                    # WHO - Teilnehmerliste zurücksenden
                    print(f"[DISCOVERY] WHO-Anfrage von {sender_ip}, bekannte Teilnehmer: {len(teilnehmer)}")
                    
                    if teilnehmer:
                        # Format: KNOWUSERS <Handle1> <IP1> <Port1>, <Handle2> <IP2> <Port2>, ...
                        teilnehmer_liste = []
                        for handle, (ip, port, _) in teilnehmer.items():
                            teilnehmer_liste.append(f"{handle} {ip} {port}")
                        
                        antwort = "KNOWUSERS " + ",".join(teilnehmer_liste)
                    else:
                        antwort = "KNOWUSERS"
                    
                    print(f"[DISCOVERY] Sende Antwort: {antwort}")
                    sock.sendto(antwort.encode("utf-8"), addresse)
                
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


def cleanup_old_participants(teilnehmer: dict, max_age: int = 300):
    """
    Cleanup-Thread: Entfernt Teilnehmer, die länger als max_age Sekunden inaktiv sind.
    
    Args:
        teilnehmer: Dictionary der aktiven Teilnehmer
        max_age: Maximales Alter in Sekunden (Standard: 5 Minuten)
    """
    while True:
        try:
            current_time = time.time()
            expired_handles = []
            
            for handle, (ip, port, last_seen) in teilnehmer.items():
                if current_time - last_seen > max_age:
                    expired_handles.append(handle)
            
            for handle in expired_handles:
                del teilnehmer[handle]
                print(f"[DISCOVERY] Teilnehmer wegen Timeout entfernt: {handle}")
            
            # Alle 5 minuten Sekunden aufräumen
            time.sleep(300)
            
        except Exception as e:
            print(f"[DISCOVERY] Cleanup-Fehler: {e}")
            time.sleep(300)