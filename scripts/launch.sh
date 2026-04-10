#!/bin/bash
# =============================================================================
# launch.sh — Lance le processus C réseau + le jeu Python (mode réparti)
#
# Exemples :
#   PC A (Hébergeur) : ./scripts/launch.sh heberger majordaft
#   PC B (Client)    : ./scripts/launch.sh rejoindre 192.168.1.10 braindead
#
# Pré-requis : WSL ou Linux
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."

MODE=$1

if [ "$MODE" != "heberger" ] && [ "$MODE" != "rejoindre" ]; then
    echo "Usage :"
    echo "  Héberger une partie :"
    echo "    ./scripts/launch.sh heberger <mon_ia>"
    echo "  Rejoindre une partie :"
    echo "    ./scripts/launch.sh rejoindre <ip_heberger> <mon_ia>"
    echo ""
    echo "IAs disponibles par défaut : majordaft, braindead"
    exit 1
fi

echo "╔═════════════════════════════════════════════════════════════╗"
echo "║             🤖 SYNCHRONISATION DES IA EN COURS...           ║"
echo "╚═════════════════════════════════════════════════════════════╝"

if [ "$MODE" == "heberger" ]; then
    MON_IA="${2:-majordaft}"
    echo "⌛ En attente que l'adversaire rejoigne le serveur TCP..."
    echo "   (Dis à ton ami(e) de faire : ./scripts/launch.sh rejoindre <TON_IP> braindead)"
    
    # Appel du script python pour l'échange TCP
    HANDSHAKE_OUTPUT=$(python3 "$SCRIPT_DIR/handshake.py" heberger "$MON_IA")

elif [ "$MODE" == "rejoindre" ]; then
    REMOTE_IP="$2"
    MON_IA="${3:-braindead}"
    
    if [ -z "$REMOTE_IP" ]; then
        echo "Erreur, IP manquante. Usage: ./scripts/launch.sh rejoindre <ip> <mon_ia>"
        exit 1
    fi
    echo "⌛ Tentative de connexion à l'hôte $REMOTE_IP..."
    
    # Appel du script python pour l'échange TCP
    HANDSHAKE_OUTPUT=$(python3 "$SCRIPT_DIR/handshake.py" rejoindre "$REMOTE_IP" "$MON_IA")
fi

# Le script affiche: "TEAM|REMOTE_IP|THEIR_IA"
IFS='|' read -r LOCAL_TEAM REMOTE_IP THEIR_IA <<< "$HANDSHAKE_OUTPUT"

# Déduction du PEER_ID
if [ "$LOCAL_TEAM" == "R" ]; then
    PEER_ID=0
    COULEUR="ROUGE 🔴 (Peer 0)"
    IA1="$MON_IA"
    IA2="$THEIR_IA"
else
    PEER_ID=1
    COULEUR="BLEU 🔵 (Peer 1)"
    IA1="$THEIR_IA"
    IA2="$MON_IA"
fi

echo ""
echo "✅ Synchronisation réussie !"
echo "==========================================="
echo "🎮 TA COULEUR   : $COULEUR"
echo "🤖 TON IA       : $MON_IA"
echo "👽 IA ADVERSE   : $THEIR_IA"
echo "🔗 IP ADVERSE   : $REMOTE_IP"
echo "==========================================="
echo ""

# ── Étape 1 : Compilation ────────────────────────────────────────────────────
echo "▶ [1/3] Compilation du processus C réseau..."
cd "$ROOT/c_network"
make c_net -s
echo "  ✓ c_network/c_net prêt"

# ── Étape 2 : Lancement de c_net ────────────────────────────────────────────
echo ""
echo "▶ [2/3] Démarrage du moteur UDP (peer=$PEER_ID, dest=$REMOTE_IP:9000)..."
./c_net "$PEER_ID" "$REMOTE_IP" &
C_PID=$!
echo "  ✓ c_net lancé en arrière-plan (PID=$C_PID)"

echo "  ⏳ Attente de la création de la zone mémoire partagée POSIX..."
sleep 1

if ! kill -0 "$C_PID" 2>/dev/null; then
    echo "  ✗ c_net s'est arrêté ! Vérifiez les erreurs ci-dessus."
    exit 1
fi
echo "  ✓ shm POSIX ouverte !"

# ── Étape 3 : Jeu Python ────────────────────────────────────────────────────
echo ""
echo "▶ [3/3] Démarrage graphique du jeu Python..."

cd "$ROOT/p_game"

# Toujours stest7 par défaut dans cette version automatisée
SCENARIO="stest7"

# IA1 = Rouge, IA2 = Bleu. On passe les arguments dans le bon ordre à engine.py
python3 main.py run "$SCENARIO" "$IA1" "$IA2" \
    --distributed --local-team "$LOCAL_TEAM"

# ── Nettoyage ────────────────────────────────────────────────────────────────
echo ""
echo "▶ Nettoyage de fin de partie..."
kill "$C_PID" 2>/dev/null && echo "  ✓ c_net arrêté" || true
cd "$ROOT/c_network"
make clean-ipc -s 2>/dev/null || true
echo "  ✓ Ressources IPC purgées"
echo "✓ Au revoir !"