#!/bin/bash
# =============================================================================
# test_connexion.sh — Test de bout-en-bout sans le jeu complet
#
# Ce script vérifie que la chaîne Python → shm → c_net → UDP fonctionne.
# Exécuter dans WSL sur les deux machines.
#
# Usage :
#   ./scripts/test_connexion.sh <mon_peer_id> <ip_du_pair>
#
# Exemples :
#   PC A : ./scripts/test_connexion.sh 0 192.168.1.2
#   PC B : ./scripts/test_connexion.sh 1 192.168.1.1
#
# Test sur une seule machine (loopback) :
#   Terminal 1 : ./scripts/test_connexion.sh 0 127.0.0.1
#   Terminal 2 : ./scripts/test_connexion.sh 1 127.0.0.1
#   ⚠ Les deux utilisent le port 9000 → le 2e bind échouera.
#   Pour le loopback, utiliser le mode --solo ci-dessous :
#   ./scripts/test_connexion.sh --solo
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

# ── Mode solo (loopback, une seule machine) ───────────────────────────────────
if [ "${1:-}" = "--solo" ]; then
    echo "=== Test Solo IPC (sans réseau) ==="
    echo ""
    cd "$ROOT/c_network"

    echo "▶ Compilation..."
    make c_net test_ipc -s
    echo "  ✓ OK"
    echo ""

    echo "▶ Lancement de c_net (peer=0, pas de pair) en arrière-plan..."
    # On lance c_net sans IP de pair (juste pour créer la shm)
    ./c_net 0 127.0.0.1 &
    C_PID=$!
    sleep 1

    if ! kill -0 "$C_PID" 2>/dev/null; then
        echo "  ✗ c_net s'est arrêté ! Vérifiez les erreurs."
        exit 1
    fi
    echo "  ✓ c_net PID=$C_PID"
    echo ""

    echo "▶ Écriture/lecture IPC via test_ipc..."
    ./test_ipc
    echo ""

    echo "▶ Test du bridge Python..."
    cd "$ROOT/p_game"
    python3 network_bridge.py 0
    echo ""

    echo "▶ Nettoyage..."
    kill "$C_PID" 2>/dev/null || true
    cd "$ROOT/c_network"
    make clean-ipc -s 2>/dev/null || true
    echo "  ✓ Ressources IPC supprimées"
    echo ""
    echo "=== Test Solo terminé ==="
    exit 0
fi

# ── Mode réseau standard ──────────────────────────────────────────────────────
PEER_ID="${1:-0}"
REMOTE_IP="${2:-}"

if [ -z "$REMOTE_IP" ]; then
    echo "Usage : $0 <mon_peer_id> <ip_du_pair>"
    echo "        $0 --solo   (test local sans réseau)"
    exit 1
fi

echo "=== Test de connexion réseau ==="
echo "  Peer ID   : $PEER_ID"
echo "  IP pair   : $REMOTE_IP:9000"
echo ""

cd "$ROOT/c_network"

# Compilation
echo "▶ Compilation..."
make c_net test_ipc -s
echo "  ✓ OK"
echo ""

# Nettoyage IPC préalable (si crash précédent)
make clean-ipc -s 2>/dev/null || true

# Lancement de c_net
echo "▶ Lancement de c_net (peer=$PEER_ID, pair=$REMOTE_IP)..."
./c_net "$PEER_ID" "$REMOTE_IP" &
C_PID=$!
sleep 1

if ! kill -0 "$C_PID" 2>/dev/null; then
    echo "  ✗ c_net s'est arrêté ! Vérifiez les erreurs."
    exit 1
fi
echo "  ✓ c_net PID=$C_PID — socket UDP ouvert sur port 9000"
echo ""

# Test IPC C-side
echo "▶ Test IPC (C) — écriture d'unités dirty dans la shm..."
./test_ipc
echo ""

# Test bridge Python
echo "▶ Test bridge Python — écriture + lecture shm..."
cd "$ROOT/p_game"
python3 network_bridge.py "$PEER_ID"
echo ""

# Surveillance 5 secondes
echo "▶ Surveillance trafic UDP pendant 5 secondes..."
echo "  (Les logs de c_net montreront les paquets envoyés/reçus)"
sleep 5

# Nettoyage
echo ""
echo "▶ Nettoyage..."
kill "$C_PID" 2>/dev/null && echo "  ✓ c_net arrêté" || true
cd "$ROOT/c_network"
make clean-ipc -s 2>/dev/null || true
echo "  ✓ Ressources IPC supprimées"
echo ""
echo "=== Test terminé ==="
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Pour tester entre 2 machines :                 ║"
echo "║    PC A : ./scripts/test_connexion.sh 0 <IP_B>  ║"
echo "║    PC B : ./scripts/test_connexion.sh 1 <IP_A>  ║"
echo "╚══════════════════════════════════════════════════╝"
