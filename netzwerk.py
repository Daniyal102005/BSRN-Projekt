from multiprocessing import Queue
import socket
import queue
import sys
import time
import threading
import os

# Broadcast-Funktionen

def send_join_broadcast(handle: str, chat_port: int, whoisport: int) -> None:
    """
    Broadcastet 'JOIN <handle> <chat_port>' an Discovery-Port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"JOIN {handle} {chat_port}"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        print(f"[JOIN] gesendet: '{message}' an Port {whoisport}")
    except Exception as e:
        print(f"Error sending JOIN broadcast: {e}")
    finally:
        sock.close()


def send_leave_broadcast(handle: str, whoisport: int) -> None:
    """
    Broadcastet 'LEAVE <handle>' an Discovery-Port.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"LEAVE {handle}"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        print(f"[LEAVE] gesendet: '{message}' an Port {whoisport}")
    except Exception as e:
        print(f"Error sending LEAVE broadcast: {e}")
    finally:
        sock.close()


def send_who_broadcast_and_wait(whoisport: int, timeout: float = 3.0, silent: bool = False) -> str:
    """
    Broadcastet 'WHO' an Discovery-Port und wartet auf Antworten.
    Sammelt alle Antworten und gibt sie zurück.
    
    Args:
        whoisport: Discovery-Port
        timeout: Timeout in Sekunden
        silent: Wenn True, werden keine Logs ausgegeben (für interne Aufrufe)
    
    Returns:
        String mit allen gefundenen Teilnehmern oder Fehlermeldung
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    all_participants = {}  # handle -> (ip, port)
    
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        # WHO-Nachricht broadcasten
        message = "WHO"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        if not silent:
            print(f"[WHO] gesendet an Port {whoisport}, warte auf Antworten...")
        
        # Sammle alle Antworten innerhalb des Timeouts
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                daten, addr = sock.recvfrom(4096)
                reply = daten.decode('utf-8').strip()
                if not silent:
                    print(f"[WHO-REPLY] von {addr[0]}: {reply}")
                
                # Parse KNOWUSERS Antwort
                if reply.startswith("KNOWUSERS"):
                    participants_str = reply[10:].strip()  # "KNOWUSERS " entfernen
                    if participants_str:  # Nicht leer
                        # Format: "Alice 192.168.1.5 5000,Bob 192.168.1.6 5001"
                        for entry in participants_str.split(','):
                            entry = entry.strip()
                            if entry:
                                parts = entry.split()
                                if len(parts) >= 3:
                                    handle, ip, port = parts[0], parts[1], parts[2]
                                    all_participants[handle] = (ip, int(port))
                
            except socket.timeout:
                # Timeout für einzelne Antwort - weitermachen
                continue
            except Exception as e:
                if not silent:
                    print(f"[WHO] Fehler beim Empfangen: {e}")
                break
        
        # Ergebnis formatieren
        if all_participants:
            result_entries = []
            for handle, (ip, port) in all_participants.items():
                result_entries.append(f"{handle} {ip} {port}")
            return ";".join(result_entries)
        else:
            return "EMPTY"
            
    except Exception as e:
        if not silent:
            print(f"Error sending WHO broadcast: {e}")
        return "ERROR"
    finally:
        sock.close()


def send_who_broadcast(whoisport: int, timeout: float = 2.0) -> None:
    """
    Vereinfachte WHO-Broadcast-Funktion für Kompatibilität mit alter UI.
    Druckt Ergebnis direkt aus.
    """
    result = send_who_broadcast_and_wait(whoisport, timeout, silent=False)
    if result == "EMPTY":
        print("[WHO-REPLY] Keine anderen Teilnehmer gefunden.")
    elif result == "ERROR":
        print("[WHO-REPLY] Fehler beim Senden der WHO-Anfrage.")
    else:
        print(f"[WHO-REPLY] Teilnehmer: {result.replace(';', ', ')}")


def send_msg(handle: str, text: str, peer_ip: str, peer_port: int) -> None:
    """
    Sendet 'MSG <handle> <text>' per TCP an einen einzelnen Peer.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect((peer_ip, peer_port))
        message = f"MSG {handle} {text}"
        tcp_socket.sendall(message.encode('utf-8'))
        print(f"[MSG] an {peer_ip}:{peer_port}: {text}")
    except Exception as e:
        print(f"Error sending MSG to {peer_ip}:{peer_port}: {e}")
    finally:
        tcp_socket.close()


def send_broadcast_message(handle: str, message: str, chat_ports: list, timeout: float = 1.0):
    """
    Sendet eine Broadcast-Nachricht an alle bekannten Chat-Clients.
    
    Args:
        handle: Sender-Handle
        message: Zu sendende Nachricht  
        chat_ports: Liste von (ip, port) Tupeln der bekannten Clients
    """
    print(f"[BROADCAST] Sende '{message}' an {len(chat_ports)} Teilnehmer...")
    
    for ip, port in chat_ports:
        try:
            # TCP-Verbindung zu jedem Client
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(timeout)
            tcp_socket.connect((ip, port))
            
            msg = f"MSG {handle} {message}"
            tcp_socket.sendall(msg.encode('utf-8'))
            print(f"[BROADCAST] -> {ip}:{port}")
            tcp_socket.close()
            
        except Exception as e:
            print(f"[BROADCAST] Fehler an {ip}:{port}: {e}")


def get_all_participants(whoisport: int, timeout: float = 2.0) -> dict:
    """
    Holt alle bekannten Teilnehmer vom Discovery-Service.
    
    Returns:
        Dictionary {handle: (ip, port)}
    """
    # SILENT WHO - keine Logs für interne Aufrufe
    result = send_who_broadcast_and_wait(whoisport, timeout, silent=True)
    participants = {}
    
    if result != "EMPTY" and result != "ERROR":
        for entry in result.split(';'):
            entry = entry.strip() 
            if entry:
                parts = entry.split()
                if len(parts) >= 3:
                    handle, ip, port = parts[0], parts[1], parts[2]
                    participants[handle] = (ip, int(port))
    
    return participants


def network_loop(ui_to_net: "Queue[str]", net_to_ui: "Queue[str]", handle: str, chat_port: int, whoisport: int):
    """
    Haupt-Loop für Chat und Discovery:
    - JOIN beim Start
    - Verarbeitet Nachrichten aus ui_to_net
    - Empfängt eingehende TCP-Nachrichten für MSG
    - Leitet WHO-Anfragen weiter und sammelt Antworten
    """
    
    # TCP-Socket für eingehende MSG-Nachrichten
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        tcp_sock.bind(("", chat_port))
        tcp_sock.listen(5)
        tcp_sock.settimeout(0.1)  # Non-blocking mit kurzen Timeouts
        
        # Initialer JOIN
        send_join_broadcast(handle, chat_port, whoisport)
        
        while True:
            # 1) Verarbeite UI-Nachrichten
            try:
                msg = ui_to_net.get_nowait()
                
                if msg == "WHO":
                    # Explizite WHO-Anfrage vom User - mit Logs
                    result = send_who_broadcast_and_wait(whoisport, timeout=3.0, silent=False)
                    if result == "EMPTY":
                        net_to_ui.put("[WHO-REPLY] Keine anderen Teilnehmer gefunden.")
                    elif result == "ERROR":
                        net_to_ui.put("[WHO-REPLY] Fehler bei WHO-Anfrage.")
                    else:
                        net_to_ui.put(f"[WHO-REPLY] {result}")
                else:
                    # Broadcast-Nachricht an alle bekannten Teilnehmer
                    participants = get_all_participants(whoisport)
                    
                    # Entferne eigenen Handle aus der Liste
                    if handle in participants:
                        del participants[handle]
                    
                    if participants:
                        chat_ports = list(participants.values())
                        send_broadcast_message(handle, msg, chat_ports)
                        net_to_ui.put(f"[BROADCAST gesendet an {len(participants)} Teilnehmer] {handle}: {msg}")
                    else:
                        net_to_ui.put(f"[BROADCAST - keine anderen Teilnehmer] {handle}: {msg}")
                    
            except queue.Empty:
                pass
            
            # 2) Empfange eingehende TCP-Verbindungen für MSG
            try:
                client_sock, client_addr = tcp_sock.accept()
                # Starte Thread für diese Verbindung
                client_thread = threading.Thread(
                    target=handle_incoming_msg, 
                    args=(client_sock, client_addr, net_to_ui),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                # Normal - kein eingehender Client
                pass
            except Exception as e:
                print(f"[NETZWERK] Fehler beim Akzeptieren von Verbindung: {e}")
            
            # Kleine Pause um CPU zu schonen
            time.sleep(0.01)
            
    except Exception as e:
        print(f"[NETZWERK] Kritischer Fehler: {e}")
    finally:
        tcp_sock.close()
        print("[NETZWERK] Netzwerk-Loop beendet")


def send_img(handle: str, image_path: str, peer_ip: str, peer_port: int) -> bool:
    """
    Sendet 'IMG <handle> <size>' per TCP an einen Peer, gefolgt von den Binärdaten.
    
    Args:
        handle: Sender-Handle
        image_path: Pfad zur zu sendenden Bilddatei
        peer_ip: IP-Adresse des Empfängers
        peer_port: TCP-Port des Empfängers
        
    Returns:
        True wenn erfolgreich, False bei Fehlern
    """
    if not os.path.exists(image_path):
        print(f"[IMG] Bilddatei nicht gefunden: {image_path}")
        return False
    
    try:
        # Dateigröße ermitteln
        file_size = os.path.getsize(image_path)
        print(f"[IMG] Sende Bild '{image_path}' ({file_size} Bytes) an {peer_ip}:{peer_port}")
        
        # TCP-Verbindung aufbauen
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((peer_ip, peer_port))
        
        # 1. IMG-Header senden
        img_header = f"IMG {handle} {file_size}\n"
        tcp_socket.sendall(img_header.encode('utf-8'))
        
        # 2. Binärdaten senden
        with open(image_path, 'rb') as img_file:
            while True:
                chunk = img_file.read(4096)  # 4KB Chunks
                if not chunk:
                    break
                tcp_socket.sendall(chunk)
        
        print(f"[IMG] Bild erfolgreich an {peer_ip}:{peer_port} gesendet")
        tcp_socket.close()
        return True
        
    except Exception as e:
        print(f"[IMG] Fehler beim Senden an {peer_ip}:{peer_port}: {e}")
        return False


def handle_incoming_msg(client_sock: socket.socket, client_addr: tuple, net_to_ui: Queue):
    """
    Verarbeitet eingehende MSG- und IMG-Nachrichten von anderen Clients.
    """
    try:
        # Ersten Teil empfangen (Header)
        data = client_sock.recv(4096)
        if data:
            # Für IMG-Nachrichten: Header und mögliche Binärdaten trennen
            if data.startswith(b"IMG"):
                # Finde das Ende der Header-Zeile (\n)
                header_end = data.find(b'\n')
                if header_end != -1:
                    header = data[:header_end].decode('utf-8', errors='ignore').strip()
                    remaining_data = data[header_end + 1:]  # Restliche Daten nach dem Header
                    print(f"[NETZWERK] IMG-Header von {client_addr}: {header}")
                    handle_incoming_img(client_sock, client_addr, header, net_to_ui, remaining_data)
                    return  # Socket wird in handle_incoming_img geschlossen
                else:
                    print(f"[NETZWERK] Ungültiger IMG-Header (kein \\n gefunden)")
                    net_to_ui.put(f"[FEHLER] Ungültiger IMG-Header von {client_addr[0]}")
            else:
                # Normal MSG-Nachricht
                message = data.decode('utf-8', errors='ignore').strip()
                print(f"[NETZWERK] Eingehende Nachricht von {client_addr}: {message}")
                
                if message.startswith("MSG"):
                    parts = message.split(maxsplit=2)
                    if len(parts) >= 3:
                        _, sender, text = parts
                        net_to_ui.put(f"[{sender}] {text}")
                    else:
                        print(f"[NETZWERK] Ungültiges MSG-Format: {message}")
                else:
                    print(f"[NETZWERK] Unbekannter Nachrichtentyp: {message}")
                
    except Exception as e:
        print(f"[NETZWERK] Fehler beim Verarbeiten eingehender Nachricht: {e}")
    finally:
        client_sock.close()


def handle_incoming_img(client_sock: socket.socket, client_addr: tuple, header: str, net_to_ui: Queue, initial_data: bytes = b""):
    """
    Verarbeitet eingehende IMG-Nachrichten und speichert Bilder lokal.
    
    Args:
        client_sock: TCP-Socket der Verbindung
        client_addr: Adresse des Senders
        header: IMG-Header ("IMG <Handle> <Size>")
        net_to_ui: Queue für UI-Nachrichten
        initial_data: Bereits empfangene Bilddaten aus dem ersten recv()
    """
    try:
        # IMG-Header parsen
        parts = header.split()
        if len(parts) < 3:
            print(f"[IMG] Ungültiger IMG-Header: {header}")
            net_to_ui.put(f"[FEHLER] Ungültiges Bildformat von {client_addr[0]}")
            return
            
        _, sender, size_str = parts
        try:
            expected_size = int(size_str)
        except ValueError:
            print(f"[IMG] Ungültige Bildgröße: {size_str}")
            net_to_ui.put(f"[FEHLER] Ungültige Bildgröße von {sender}")
            return
        
        print(f"[IMG] Empfange Bild von {sender} ({expected_size} Bytes)")
        
        # Bilddaten empfangen
        received_data = initial_data  # Beginne mit bereits empfangenen Daten
        remaining = expected_size - len(initial_data)
        
        while remaining > 0:
            chunk_size = min(4096, remaining)
            chunk = client_sock.recv(chunk_size)
            if not chunk:
                print(f"[IMG] Verbindung unterbrochen (erwartet: {expected_size}, erhalten: {len(received_data)})")
                net_to_ui.put(f"[FEHLER] Bild von {sender} unvollständig empfangen")
                return
            
            received_data += chunk
            remaining -= len(chunk)
        
        # Dateiname generieren (mit Zeitstempel für Eindeutigkeit)
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{sender}_{timestamp}.jpg"  # Standardmäßig .jpg
        
        # Bildverzeichnis aus config.toml oder Standard
        try:
            import toml
            config = toml.load("config.toml")
            image_dir = config.get("imagepath", "./images")
        except:
            image_dir = "./images"
        
        # Verzeichnis erstellen falls nicht vorhanden
        os.makedirs(image_dir, exist_ok=True)
        
        # Vollständiger Pfad
        full_path = os.path.join(image_dir, filename)
        
        # Bild speichern
        with open(full_path, 'wb') as img_file:
            img_file.write(received_data)
        
        print(f"[IMG] Bild von {sender} gespeichert: {full_path}")
        net_to_ui.put(f"[📷 BILD] {sender} hat ein Bild gesendet → {full_path}")
        
        # Optional: Bildbetrachter öffnen (Windows)
        try:
            import subprocess
            import platform
            if platform.system() == "Windows":
                subprocess.run(['start', full_path], shell=True, check=False)
                print(f"[IMG] Bildbetrachter geöffnet für: {full_path}")
        except:
            pass  # Wenn Bildbetrachter nicht funktioniert, ignorieren
            
    except Exception as e:
        print(f"[IMG] Fehler beim Empfangen von Bild: {e}")
        net_to_ui.put(f"[FEHLER] Bild von {client_addr[0]} konnte nicht gespeichert werden")
    finally:
        client_sock.close()


if __name__ == "__main__":
    # Test-Code falls direkt ausgeführt
    print("Netzwerk-Modul - Test-Modus")
    send_who_broadcast(4000)