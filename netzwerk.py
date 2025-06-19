"""
Dieses Modul stellt alle Netzwerk-Funktionen für JOIN, LEAVE, WHO und MSG bereit.
Es liest einmalig die zentrale config.toml und verschickt Broadcasts an den
Discovery-Port sowie direkte TCP-Nachrichten an Peers.
"""

import socket
import toml
import sys

def load_config(config_path: str = 'config.toml') -> dict:
    """
    Lädt die Konfiguration aus der angegebenen TOML-Datei.
    Erwartete Keys: handle (str), port (int), whoisport (int)
    """
    try:
        with open(config_path, 'r') as f:
            return toml.load(f)
    except Exception as e:
        print(f"Fehler beim Laden der Config '{config_path}': {e}")
        return {}

def send_join_broadcast(handle: str, chat_port: int, whoisport: int) -> None:
    """
    Broadcastet 'JOIN <handle> <chat_port>' an alle Teilnehmer via UDP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"JOIN {handle} {chat_port}\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        print(f"[JOIN] gesendet: '{message.strip()}' an Port {whoisport}")
    except Exception as e:
        print(f"Error sending JOIN broadcast: {e}")
    finally:
        sock.close()

def send_leave_broadcast(handle: str, whoisport: int) -> None:
    """
    Broadcastet 'LEAVE <handle>' an alle Teilnehmer via UDP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"LEAVE {handle}\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        print(f"[LEAVE] gesendet: '{message.strip()}' an Port {whoisport}")
    except Exception as e:
        print(f"Error sending LEAVE broadcast: {e}")
    finally:
        sock.close()

def send_who_broadcast(whoisport: int, timeout: float = 2.0) -> None:
    """
    Broadcastet 'WHO' an Discovery-Port und wartet auf eine Antwort.
    Gibt die Antwort oder einen Timeout-Hinweis aus.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = "WHO\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', whoisport))
        print(f"[WHO] gesendet an Port {whoisport}, warte auf Antwort…")
        sock.settimeout(timeout)
        try:
            daten, addr = sock.recvfrom(4096)
            reply = daten.decode('utf-8').strip()
            print(f"[WHO-REPLY] von {addr}: {reply}")
        except socket.timeout:
            print("[WHO-REPLY] kein Antwort erhalten (Timeout).")
    except Exception as e:
        print(f"Error sending WHO broadcast: {e}")
    finally:
        sock.close()

def send_msg(handle: str, text: str, peer_ip: str, peer_port: int) -> None:
    """
    Sendet 'MSG <handle> <text>' per TCP an einen einzelnen Peer.
    """
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_socket.connect((peer_ip, peer_port))
        message = f"MSG {handle} {text}\n"
        tcp_socket.sendall(message.encode('utf-8'))
        print(f"[MSG] an {peer_ip}:{peer_port}: {text}")
    except Exception as e:
        print(f"Error sending MSG to {peer_ip}:{peer_port}: {e}")
    finally:
        tcp_socket.close()

if _name_ == "_main_":
    cfg = load_config('config.toml')
    if not cfg:
        sys.exit(1)

    handle    = cfg.get('handle', 'User')
    port      = cfg.get('port', 5000)
    whoisport = cfg.get('whoisport', 4000)

    send_join_broadcast(handle, port, whoisport)
    send_who_broadcast(whoisport)
    send_leave_broadcast(handle, whoisport)
