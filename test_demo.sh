#!/bin/bash

# Script de test : Démonstration du système de propriété réseau
# Utilise localhost (127.0.0.1) avec les ports 5555 et 5556

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Démonstration: Système de Propriété Réseau              ║${NC}"
echo -e "${BLUE}║  Points 1-7 — Demande, Concession, Synchronisation        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Vérifications préalables
echo -e "${YELLOW}[SETUP] Vérifications...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 introuvable${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 détecté${NC}"

if [ ! -f "c_network/c_net" ]; then
    echo -e "${YELLOW}[BUILD] Compilation du processus C...${NC}"
    cd c_network
    make clean > /dev/null 2>&1
    make > /dev/null 2>&1
    if [ -f "c_net" ]; then
        echo -e "${GREEN}✓ Processus C compilé${NC}"
    else
        echo -e "${RED}✗ Compilation échouée${NC}"
        exit 1
    fi
    cd ..
fi

# Ports
PORT_PEER0=5555
PORT_PEER1=5556

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ÉTAPE 1: Lancer Peer 0 (Processus Réseau)                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Commande:${NC} ./c_network/c_net 0 127.0.0.1:${PORT_PEER1}"
echo ""
echo -e "${YELLOW}Attendez les logs:${NC}"
echo -e "  [DEMO-SHAKE] Peer 0 envoie HELLO"
echo -e "  ... (en attente de Peer 1)"
echo ""

cd c_network
./c_net 0 127.0.0.1:${PORT_PEER1} 2>&1 | while read line; do
    if echo "$line" | grep -q "DEMO-SHAKE"; then
        echo -e "${GREEN}[C-NET P0]${NC} $line"
    elif echo "$line" | grep -q "DEMO-NET"; then
        echo -e "${GREEN}[C-NET P0]${NC} $line"
    elif echo "$line" | grep -q "DEMO-OWN"; then
        echo -e "${BLUE}[C-NET P0]${NC} $line"
    elif echo "$line" | grep -q "DEMO-SYNC"; then
        echo -e "${BLUE}[C-NET P0]${NC} $line"
    elif echo "$line" | grep -q "Handshake complet"; then
        echo -e "${GREEN}[C-NET P0]${NC} $line"
    fi
done &
PEER0_PID=$!
cd ..

sleep 2

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ÉTAPE 2: Lancer Peer 1 (Processus Réseau)                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Commande:${NC} NET_PORT=${PORT_PEER1} ./c_network/c_net 1 127.0.0.1:${PORT_PEER0}"
echo ""
echo -e "${YELLOW}Attendez les logs:${NC}"
echo -e "  [DEMO-SHAKE] Peer 1 envoie HELLO"
echo -e "  [DEMO-SHAKE] Peer 1 reçu HELLO de peer 0"
echo -e "  [DEMO-SHAKE] ✓ Handshake complet"
echo ""

cd c_network
NET_PORT=${PORT_PEER1} ./c_net 1 127.0.0.1:${PORT_PEER0} 2>&1 | while read line; do
    if echo "$line" | grep -q "DEMO-SHAKE"; then
        echo -e "${GREEN}[C-NET P1]${NC} $line"
    elif echo "$line" | grep -q "DEMO-NET"; then
        echo -e "${GREEN}[C-NET P1]${NC} $line"
    elif echo "$line" | grep -q "DEMO-OWN"; then
        echo -e "${BLUE}[C-NET P1]${NC} $line"
    elif echo "$line" | grep -q "DEMO-SYNC"; then
        echo -e "${BLUE}[C-NET P1]${NC} $line"
    elif echo "$line" | grep -q "Handshake complet"; then
        echo -e "${GREEN}[C-NET P1]${NC} $line"
    fi
done &
PEER1_PID=$!
cd ..

sleep 3

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ÉTAPE 3: Lancer Jeu Peer 0 (Équipe Rouge)                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Commande:${NC} python3 main.py run stest7 smart_ia brain_dead \\"
echo -e "            --distributed --local-team R --terminal"
echo ""
echo -e "${YELLOW}Attendez les logs de démonstration:${NC}"
echo -e "  [DEMO-DECIDE] IA décide pour unit"
echo -e "  [DEMO-ACTION] Exécution"
echo -e "  [DEMO-BROADCAST] Broadcast"
echo ""

cd p_game
python3 main.py run stest7 smart_ia brain_dead \
    --distributed --local-team R --terminal 2>&1 | while read line; do
    if echo "$line" | grep -q "DEMO-"; then
        echo -e "${YELLOW}[GAME P0]${NC} $line"
    fi
done &
GAME0_PID=$!
cd ..

sleep 2

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ÉTAPE 4: Lancer Jeu Peer 1 (Équipe Bleue)                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Commande:${NC} NET_PORT=${PORT_PEER1} python3 main.py run stest7 brain_dead smart_ia \\"
echo -e "            --distributed --local-team B --terminal"
echo ""
echo -e "${YELLOW}Attendez la synchronisation réseau...${NC}"
echo ""

cd p_game
NET_PORT=${PORT_PEER1} python3 main.py run stest7 brain_dead smart_ia \
    --distributed --local-team B --terminal 2>&1 | while read line; do
    if echo "$line" | grep -q "DEMO-"; then
        echo -e "${YELLOW}[GAME P1]${NC} $line"
    fi
done &
GAME1_PID=$!
cd ..

# Attendez 30 secondes de démonstration
echo ""
echo -e "${GREEN}[INFO] Démonstration en cours (30 secondes)...${NC}"
sleep 30

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  RÉSUMÉ: Points Démontrés                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Point 1: Un jeu demande la propriété réseau${NC}"
echo -e "  → Voir logs [DEMO-REQ] et [DEMO-DECIDE]"
echo ""
echo -e "${GREEN}✓ Point 2: Le propriétaire envoie propriété + état${NC}"
echo -e "  → Voir logs [DEMO-OWN] ✓ ACCORDE et [DEMO-NET]"
echo ""
echo -e "${GREEN}✓ Point 3: Le demandeur vérifie action possible${NC}"
echo -e "  → Voir logs [DEMO-SYNC] ✓ Propriété ACQUISE"
echo ""
echo -e "${GREEN}✓ Point 4: Mise à jour visuelle locale${NC}"
echo -e "  → Units se déplacent dans l'affichage terminal"
echo ""
echo -e "${GREEN}✓ Point 5: Transmission pour participants distants${NC}"
echo -e "  → Voir logs [DEMO-BROADCAST]"
echo ""
echo -e "${GREEN}✓ Point 6: Réception et application distante${NC}"
echo -e "  → Voir logs [DEMO-SYNC] reçu état unite"
echo ""
echo -e "${GREEN}✓ Point 7: Déroulement cohérent et démontrable${NC}"
echo -e "  → Logs temps-réel affichent l'ordre complet des actions"
echo ""

echo -e "${YELLOW}[CLEANUP] Arrêt des processus...${NC}"
kill $PEER0_PID 2>/dev/null || true
kill $PEER1_PID 2>/dev/null || true
kill $GAME0_PID 2>/dev/null || true
kill $GAME1_PID 2>/dev/null || true
wait 2>/dev/null || true

echo -e "${GREEN}[DONE]${NC} Démonstration terminée"
echo ""
echo "Pour capturer les logs complets, lancez:"
echo -e "  ${BLUE}./c_network/c_net 0 127.0.0.1:5556 2>&1 | grep DEMO-${NC}"
echo -e "  ${BLUE}NET_PORT=5556 ./c_network/c_net 1 127.0.0.1:5555 2>&1 | grep DEMO-${NC}"
echo -e "  ${BLUE}cd p_game && python3 main.py run stest7 smart_ia brain_dead ... 2>&1 | grep DEMO-${NC}"
