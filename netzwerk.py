import socket
try:
    import toml
except ImportError:
    print("Error: toml library not found. Please install it with 'pip install toml'")
    exit(1)

# Lädt die Konfiguration aus der Datei config.toml
def load_config(config_path: str = 'config.toml') -> dict:
    try:
        with open(config_path, 'r') as f:
            return toml.load(f)
    except Exception as e:
        print("Fehler beim Laden der Config:", e)
        return {}

# Sendet eine JOIN-Nachricht per UDP-Broadcast an Port 4000
def send_join_broadcast(handle: str, port: int) -> None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"JOIN {handle} {port}\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', 4000))
        print(f"Sent JOIN broadcast: {message.strip()}")
    except Exception as e:
        print(f"Error sending JOIN broadcast: {e}")

# Sendet eine LEAVE-Nachricht per UDP-Broadcast
def send_leave_broadcast(handle: str) -> None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = f"LEAVE {handle}\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', 4000))
        print(f"Sent LEAVE broadcast: {message.strip()}")
    except Exception as e:
        print(f"Error sending LEAVE broadcast: {e}")

# Sendet eine MSG-Nachricht per TCP an einen bestimmten Peer
def send_msg(handle: str, text: str, peer_ip: str, peer_port: int) -> None:
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((peer_ip, peer_port))
        message = f'MSG {handle} "{text}"\n'
        tcp_socket.sendall(message.encode('utf-8'))
        tcp_socket.close()
        print(f"Sent MSG to {peer_ip}:{peer_port}")
    except Exception as e:
        print(f"Error sending MSG to {peer_ip}:{peer_port}: {e}")

# Sendet eine WHO-Anfrage per UDP-Broadcast
def send_who_broadcast() -> None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = "WHO\n"
        sock.sendto(message.encode('utf-8'), ('255.255.255.255', 4000))
        print("WHO gesendet")
        sock.close()
    except Exception as e:
        print(f"Error sending WHO broadcast: {e}")

# Hauptprogramm
if _name_ == "_main_":
    config = load_config()
    if config:
        handle = config.get('handle', 'DefaultHandle')
        port = config.get('port', 12000)

        # Test JOIN und WHO – die Discovery-Komponente antwortet separat
        send_join_broadcast(handle, port)
        send_who_broadcast()

        # LEAVE-Test (optional, z. B. beim Beenden)
        send_leave_broadcast(handle)

        # MSG-Test entfällt hier – da Peer-Daten aus Discovery kommen sollten
        # → Wird später durch IPC/Controller angestoßen
