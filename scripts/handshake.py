import socket
import sys
import time

if len(sys.argv) < 3:
    sys.exit(1)

mode = sys.argv[1]

# Port de synchronisation initial
PORT = 9005

if mode == "heberger":
    my_ia = sys.argv[2]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", PORT))
    s.listen(1)
    conn, addr = s.accept()
    
    # Échange
    their_ia = conn.recv(1024).decode('utf-8').strip()
    conn.send(my_ia.encode('utf-8'))
    
    conn.close()
    s.close()
    
    # Format de sortie: TEAM REMOTE_IP THEIR_IA
    print(f"R|{addr[0]}|{their_ia}")
    
elif mode == "rejoindre":
    ip = sys.argv[2]
    my_ia = sys.argv[3]
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Tente de se connecter
    connected = False
    for _ in range(60): # 1 minute max pour rejoindre
        try:
            s.connect((ip, PORT))
            connected = True
            break
        except ConnectionRefusedError:
            time.sleep(1)
            
    if not connected:
        sys.exit(1)
        
    s.send(my_ia.encode('utf-8'))
    their_ia = s.recv(1024).decode('utf-8').strip()
    s.close()
    
    # Format de sortie: TEAM REMOTE_IP THEIR_IA
    print(f"B|{ip}|{their_ia}")
