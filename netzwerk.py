from multiprocessing import Queue
import socket
import queue
import sys
import time
import threading
import os

##
# @file chat_network.py
# @brief Netzwerkfunktionen für Chat-Programm mit Discovery via UDP-Broadcast und TCP-Kommunikation.
# 
# Enthält Funktionen zum Senden und Empfangen von JOIN, LEAVE, WHO Broadcasts,
# Nachrichten (MSG) und Bildern (IMG).
# Außerdem einen Haupt-Netzwerkloop zur Verwaltung von Verbindungen.
#

##
# @brief Sendet einen JOIN-Broadcast.
# 
# Sendet die Nachricht "JOIN <handle> <chat_port>" an den Discovery-Port per UDP-Broadcast.
# 
# @param handle Benutzername/Handle als String
# @param chat_port TCP-Port, auf dem der Chat läuft
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
#
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

##
# @brief Sendet einen LEAVE-Broadcast.
# 
# Sendet die Nachricht "LEAVE <handle>" an den Discovery-Port per UDP-Broadcast.
# 
# @param handle Benutzername/Handle als String
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
#
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

##
# @brief Sendet eine WHO-Anfrage per Broadcast und wartet auf Antworten.
# 
# Sendet "WHO" an den Discovery-Port und sammelt alle eingehenden Antworten innerhalb eines Timeouts.
# 
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
# @param timeout Zeit in Sekunden, wie lange auf Antworten gewartet wird (Standard 3.0s)
# @param silent Wenn True, werden keine Konsolenlogs ausgegeben (für interne Aufrufe)
# 
# @return String mit allen gefundenen Teilnehmern im Format "Handle IP Port;Handle IP Port;..." oder "EMPTY" / "ERROR"
#
def send_who_broadcast_and_wait(whoisport: int, timeout: float = 3.0, silent: bool = False) -> str:
    """
    Broadcastet 'WHO' an Discovery-Port und wartet auf Antworten.
    Sammelt alle Antworten und gibt sie zurück.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    all_participants = {}  # handle -> (ip, port)
    
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        message = "WHO"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        if not silent:
            print(f"[WHO] gesendet an Port {whoisport}, warte auf Antworten...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                daten, addr = sock.recvfrom(4096)
                reply = daten.decode('utf-8').strip()
                if not silent:
                    print(f"[WHO-REPLY] von {addr[0]}: {reply}")
                
                if reply.startswith("KNOWUSERS"):
                    participants_str = reply[10:].strip()
                    if participants_str:
                        for entry in participants_str.split(','):
                            entry = entry.strip()
                            if entry:
                                parts = entry.split()
                                if len(parts) >= 3:
                                    handle, ip, port = parts[0], parts[1], parts[2]
                                    all_participants[handle] = (ip, int(port))
                
            except socket.timeout:
                continue
            except Exception as e:
                if not silent:
                    print(f"[WHO] Fehler beim Empfangen: {e}")
                break
        
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

##
# @brief Sendet eine WHO-Anfrage (ohne Rückgabe).
# 
# Funktion für UI-Kompatibilität, die das Ergebnis direkt auf die Konsole schreibt.
# 
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
# @param timeout Timeout für das Warten auf Antworten (Standard 2.0s)
#
def send_who_broadcast(whoisport: int, timeout: float = 2.0) -> None:
    """
    Vereinfachte WHO-Broadcast-Funktion für Kompatibilität mit alter UI.
    """
    result = send_who_broadcast_and_wait(whoisport, timeout, silent=False)
    if result == "EMPTY":
        print("[WHO-REPLY] Keine anderen Teilnehmer gefunden.")
    elif result == "ERROR":
        print("[WHO-REPLY] Fehler beim Senden der WHO-Anfrage.")
    else:
        print(f"[WHO-REPLY] Teilnehmer: {result.replace(';', ', ')}")

##
# @brief Sendet eine MSG-Nachricht per TCP an einen Peer.
# 
# @param handle Sender-Handle als String
# @param text Nachrichtentext als String
# @param peer_ip IP-Adresse des Empfängers
# @param peer_port TCP-Port des Empfängers
#
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

##
# @brief Sendet eine Broadcast-Nachricht an alle bekannten Chat-Clients.
# 
# @param handle Sender-Handle als String
# @param message Nachrichtentext als String
# @param chat_ports Liste von (IP, Port)-Tupeln bekannter Clients
# @param timeout Timeout für TCP-Verbindungen (Standard 1 Sekunde)
#
def send_broadcast_message(handle: str, message: str, chat_ports: list, timeout: float = 1.0):
    """
    Sendet eine Broadcast-Nachricht an alle bekannten Chat-Clients.
    """
    print(f"[BROADCAST] Sende '{message}' an {len(chat_ports)} Teilnehmer...")
    
    for ip, port in chat_ports:
        try:
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.settimeout(timeout)
            tcp_socket.connect((ip, port))
            msg = f"MSG {handle} {message}"
            tcp_socket.sendall(msg.encode('utf-8'))
            print(f"[BROADCAST] -> {ip}:{port}")
            tcp_socket.close()
        except Exception as e:
            print(f"[BROADCAST] Fehler an {ip}:{port}: {e}")

##
# @brief Holt alle bekannten Teilnehmer vom Discovery-Service.
# 
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
# @param timeout Timeout für WHO-Anfrage (Standard 2 Sekunden)
# 
# @return Dictionary mit {handle: (ip, port)}
#
def get_all_participants(whoisport: int, timeout: float = 2.0) -> dict:
    """
    Holt alle bekannten Teilnehmer vom Discovery-Service.
    """
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

##
# @brief Sendet ein Bild per TCP an einen Peer.
# 
# Sendet zuerst einen Header mit Größe und dann die Binärdaten.
# 
# @param handle Sender-Handle als String
# @param image_path Pfad zur Bilddatei
# @param peer_ip IP-Adresse des Empfängers
# @param peer_port TCP-Port des Empfängers
# @return True bei Erfolg, False bei Fehler
#
def send_img(handle: str, image_path: str, peer_ip: str, peer_port: int) -> bool:
    """
    Sendet ein Bild an einen Peer per TCP.
    """
    try:
        filesize = os.path.getsize(image_path)
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((peer_ip, peer_port))
        
        header = f"IMG {handle} {filesize}\n"
        tcp_socket.sendall(header.encode('utf-8'))
        
        with open(image_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                tcp_socket.sendall(chunk)
        
        tcp_socket.close()
        print(f"[IMG] Bild {image_path} gesendet an {peer_ip}:{peer_port}")
        return True
    except Exception as e:
        print(f"Fehler beim Senden des Bildes: {e}")
        return False

##
# @brief Verarbeitet eingehende Nachrichten von einem Client-Socket.
# 
# Wird in einem Thread ausgeführt, um parallele Verarbeitungen zu ermöglichen.
# 
# @param client_sock Socket des eingehenden Clients
# @param client_addr Adresse des Clients (IP, Port)
# @param net_to_ui Queue für die Kommunikation zur UI
#
def handle_incoming_msg(client_sock: socket.socket, client_addr: tuple, net_to_ui: Queue):
    """
    Verarbeitet eine eingehende Nachricht von einem Client.
    Unterstützt MSG und IMG.
    """
    try:
        data = client_sock.recv(4096)
        if not data:
            client_sock.close()
            return
        text = data.decode('utf-8', errors='ignore').strip()
        if text.startswith("IMG"):
            handle_incoming_img(client_sock, client_addr, text, net_to_ui, initial_data=b"")
        elif text.startswith("MSG"):
            # Format: MSG <handle> <text>
            parts = text.split(' ', 2)
            if len(parts) >= 3:
                _, handle, msg_text = parts
                net_to_ui.put(f"MSG {handle}: {msg_text}")
                print(f"[RECV MSG] von {handle}: {msg_text}")
            else:
                print(f"[RECV MSG] Ungültiges MSG-Format: {text}")
        else:
            print(f"[RECV] Unbekannter Nachrichtentyp: {text}")
    except Exception as e:
        print(f"Fehler beim Verarbeiten eingehender Nachricht: {e}")
    finally:
        client_sock.close()

##
# @brief Verarbeitet eingehende Bilddaten.
# 
# Empfängt den Header, liest die angegebene Anzahl von Bytes und speichert das Bild.
# 
# @param client_sock Socket des eingehenden Clients
# @param client_addr Adresse des Clients (IP, Port)
# @param header Header-Zeile mit "IMG <handle> <size>"
# @param net_to_ui Queue für die Kommunikation zur UI
# @param initial_data Bereits empfangene Bilddaten (optional)
#
def handle_incoming_img(client_sock: socket.socket, client_addr: tuple, header: str, net_to_ui: Queue, initial_data: bytes = b""):
    """
    Empfängt und speichert ein Bild, das per TCP übertragen wurde.
    """
    try:
        parts = header.split()
        if len(parts) < 3:
            print(f"[IMG] Ungültiger Header: {header}")
            client_sock.close()
            return
        _, handle, size_str = parts
        size = int(size_str)
        
        print(f"[IMG] Empfang von Bild von {handle}, Größe: {size} Bytes")
        
        received_data = initial_data
        while len(received_data) < size:
            chunk = client_sock.recv(4096)
            if not chunk:
                break
            received_data += chunk
        
        if len(received_data) != size:
            print(f"[IMG] Fehler: Erwartet {size} Bytes, erhalten {len(received_data)} Bytes")
            client_sock.close()
            return
        
        image_dir = "./images"
        os.makedirs(image_dir, exist_ok=True)
        filename = f"{handle}_{int(time.time())}.png"
        filepath = os.path.join(image_dir, filename)
        
        with open(filepath, "wb") as img_file:
            img_file.write(received_data)
        
        print(f"[IMG] Bild gespeichert unter: {filepath}")
        net_to_ui.put(f"IMG {handle} {filepath}")
        
        # Optional: Bild anzeigen unter Windows
        if sys.platform == "win32":
            os.startfile(filepath)
        
    except Exception as e:
        print(f"Fehler beim Empfang des Bildes: {e}")
    finally:
        client_sock.close()

##
# @brief Haupt-Netzwerkloop für das Chatprogramm.
# 
# - Sendet initialen JOIN-Broadcast.
# - Empfängt Nachrichten vom UI (ui_to_net).
# - Sendet Nachrichten per Broadcast.
# - Empfängt eingehende TCP-Verbindungen.
# - Übergibt eingehende Nachrichten an die UI (net_to_ui).
# 
# @param ui_to_net Queue zum Empfang von UI-Nachrichten (Befehle und Texte)
# @param net_to_ui Queue zur Weitergabe von eingehenden Nachrichten an die UI
# @param handle Benutzername/Handle
# @param chat_port TCP-Port für Chat-Verbindungen
# @param whoisport UDP-Port für Discovery (WHOIS-Port)
#
def network_loop(ui_to_net: Queue, net_to_ui: Queue, handle: str, chat_port: int, whoisport: int):
    """
    Hauptloop für Netzwerkkommunikation.
    """
    send_join_broadcast(handle, chat_port, whoisport)
    
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server.bind(('', chat_port))
    tcp_server.listen(5)
    tcp_server.setblocking(False)
    
    print(f"[NET] Netzwerkloop gestartet. Warte auf Verbindungen auf Port {chat_port}")
    
    try:
        while True:
            # Verarbeite UI-Nachrichten
            try:
                message = ui_to_net.get_nowait()
                if message == "WHO":
                    print("[NET] WHO-Anfrage erhalten.")
                    participants_str = send_who_broadcast_and_wait(whoisport)
                    net_to_ui.put(f"WHO-REPLY {participants_str}")
                else:
                    # Nachricht an alle anderen senden
                    participants = get_all_participants(whoisport)
                    # Filter eigene IP und Port herausnehmen
                    chat_ports = [(ip, port) for h, (ip, port) in participants.items() if h != handle]
                    send_broadcast_message(handle, message, chat_ports)
            except queue.Empty:
                pass
            
            # Neue TCP-Verbindung annehmen
            try:
                client_sock, client_addr = tcp_server.accept()
                print(f"[NET] Neue Verbindung von {client_addr}")
                threading.Thread(target=handle_incoming_msg, args=(client_sock, client_addr, net_to_ui), daemon=True).start()
            except BlockingIOError:
                # Kein neuer Verbindungswunsch
                pass
            
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("[NET] Netzwerkloop wird beendet.")
    finally:
        send_leave_broadcast(handle, whoisport)
        tcp_server.close()
