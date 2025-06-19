import socket
import queue
import sys

# Broadcast-Funktionen

def send_join_broadcast(handle: str, chat_port: int, whoisport: int) -> None:
    """
    Broadcastet 'JOIN <handle> <chat_port>' an Discovery-Port.
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
    Broadcastet 'LEAVE <handle>' an Discovery-Port.
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
    Antwort wird auf stdout geschrieben.
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


def network_loop(ui_to_net: "Queue[str]", net_to_ui: "Queue[str]", handle: str, chat_port: int, whoisport: int):
    """
    Haupt-Loop für Chat und Discovery:
    - JOIN beim Start
    - Nachrichten aus ui_to_net als "MSG ..." broadcasten
    - WHO-Anfragen aus ui_to_net broadcasten
    - eingehende UDP-Pakete empfangen und an net_to_ui weitergeben
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("", chat_port))

    # Initialer JOIN
    send_join_broadcast(handle, chat_port, whoisport)

    while True:
        # 1) Sende UI-Nachrichten
        try:
            msg = ui_to_net.get_nowait()
            if msg == "WHO":
                send_who_broadcast(whoisport)
            else:
                packet = f"MSG {handle} {msg}\n".encode('utf-8')
                sock.sendto(packet, ('255.255.255.255', chat_port))
        except queue.Empty:
            pass

        # 2) Empfange eingehende Pakete
        try:
            data, addr = sock.recvfrom(4096)
            text = data.decode('utf-8', errors='ignore').strip()
            if text.startswith("MSG"):
                _, sender, body = text.split(maxsplit=2)
                net_to_ui.put(f"{sender}: {body}")
            elif text.startswith("KNOWNUSERS"):
                entries = text.split(' ', 1)[1]
                net_to_ui.put(f"[WHO-REPLY] {entries}")
        except Exception:
            pass