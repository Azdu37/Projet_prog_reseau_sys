#!/bin/bash
# =============================================================================
# launch.sh — Lance le processus C réseau + le jeu Python (mode réparti)
#
# Usage (dans WSL) :
#   ./scripts/launch.sh <mon_peer_id> <ip_du_pair> [scenario] [ia1] [ia2]
#
# Exemples :
#   PC A (peer 0) : ./scripts/launch.sh 0 192.168.1.2
#   PC B (peer 1) : ./scripts/launch.sh 1 192.168.1.1
#
# Pré-requis :
#   - WSL ou Linux (shm POSIX + sockets UDP)
#   - gcc installé  (sudo apt install gcc)
#   - python3       (sudo apt install python3)
# =============================================================================
set -e

PEER_ID="${1:-0}"
REMOTE_IP="${2:-127.0.0.1}"
SCENARIO="${3:-stest7}"
IA1="${4:-majordaft}"
IA2="${5:-brain_dead}"

# Équipe locale : peer 0 = Rouge (R), peer 1 = Bleu (B)
if [ "$PEER_ID" -eq 0 ]; then
    LOCAL_TEAM="R"
else
    LOCAL_TEAM="B"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "╔══════════════════════════════════════════╗"
echo "║         Lancement mode réparti          ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Peer ID    : $PEER_ID"
echo "║  IP du pair : $REMOTE_IP"
echo "║  Équipe     : $LOCAL_TEAM"
echo "║  Scénario   : $SCENARIO"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Étape 1 : Compilation ────────────────────────────────────────────────────
echo "▶ [1/3] Compilation du processus C réseau..."
cd "$ROOT/c_network"
make c_net -s
echo "  ✓ c_network/c_net compilé"

# ── Étape 2 : Lancement de c_net ────────────────────────────────────────────
echo ""
echo "▶ [2/3] Démarrage de c_net (peer=$PEER_ID, pair=$REMOTE_IP:9000)..."
./c_net "$PEER_ID" "$REMOTE_IP" &
C_PID=$!
echo "  ✓ c_net lancé (PID=$C_PID)"

# Attendre que la shm soit créée par c_net
echo "  ⏳ Attente de la shm..."
sleep 1

# Vérifier que c_net tourne encore
if ! kill -0 "$C_PID" 2>/dev/null; then
    echo "  ✗ c_net s'est arrêté ! Vérifiez les erreurs ci-dessus."
    exit 1
fi
echo "  ✓ shm prête"

# ── Étape 3 : Jeu Python ────────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Démarrage du jeu Python..."
echo "  Scénario  : $SCENARIO"
echo "  IA        : $IA1 vs $IA2"
echo "  Équipe    : $LOCAL_TEAM (peer $PEER_ID)"
echo ""

cd "$ROOT/p_game"
python3 main.py run "$SCENARIO" "$IA1" "$IA2" \
    --distributed --local-team "$LOCAL_TEAM"

# ── Nettoyage ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Nettoyage..."
kill "$C_PID" 2>/dev/null && echo "  ✓ c_net arrêté" || true
cd "$ROOT/c_network"
make clean-ipc -s 2>/dev/null || true
echo "  ✓ Ressources IPC supprimées"
echo ""
echo "✓ Terminé."