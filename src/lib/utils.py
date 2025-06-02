import socket
from socket import AF_INET, SOCK_DGRAM

def get_local_ip() -> str:
    s = socket.socket(AF_INET, SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

