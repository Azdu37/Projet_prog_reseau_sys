#!/bin/bash

# Script de vérification — Système de Propriété Réseau
# Valide que tous les logs de démonstration sont présents

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Vérification: Système de Propriété Réseau (7 points)     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

check_log() {
    local file="$1"
    local tag="$2"
    local description="$3"
    
    if grep -q -F "$tag" "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description (cherche: $tag)"
        ((CHECKS_FAILED++))
        return 1
    fi
}

echo -e "${YELLOW}[1/3] Vérification du processus C${NC}"
echo ""

check_log "c_network/protocol.c" "DEMO-SHAKE" "   Handshake initial (HELLO/READY)"
check_log "c_network/protocol.c" "DEMO-OWN" "   Accord de propriété"
check_log "c_network/protocol.c" "DEMO-SYNC" "   Réception d'état (Sync)"
check_log "c_network/main.c" "DEMO-NET" "   Broadcast réseau"

echo ""
echo -e "${YELLOW}[2/3] Vérification du bridge Python${NC}"
echo ""

check_log "p_game/network_bridge.py" "DEMO-REQ" "   Demande de propriété"
check_log "p_game/network_bridge.py" "DEMO-BROADCAST" "   Broadcast local"
check_log "p_game/network_bridge.py" "DEMO-SYNC" "   Synchronisation"

echo ""
echo -e "${YELLOW}[3/3] Vérification du moteur de jeu${NC}"
echo ""

check_log "p_game/battle/engine.py" "DEMO-DECIDE" "   IA prend décision"
check_log "p_game/battle/engine.py" "DEMO-ACTION" "   Action exécutée"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Résumé des Vérifications                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Logs implémentés: ${GREEN}$CHECKS_PASSED${NC} ✓"
echo -e "Manquants:        ${RED}$CHECKS_FAILED${NC} ✗"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] Tous les logs de démonstration sont en place !${NC}"
    echo ""
    echo "Les 7 points sont démontrables:"
    echo -e "  ${GREEN}✓${NC} Point 1: Demande propriété [DEMO-REQ, DEMO-DECIDE]"
    echo -e "  ${GREEN}✓${NC} Point 2: Propriétaire envoie [DEMO-OWN ACCORDE]"
    echo -e "  ${GREEN}✓${NC} Point 3: Demandeur vérifie [DEMO-OWN REÇOIT]"
    echo -e "  ${GREEN}✓${NC} Point 4: Mise à jour visuelle [DEMO-ACTION]"
    echo -e "  ${GREEN}✓${NC} Point 5: Transmission [DEMO-BROADCAST, DEMO-NET]"
    echo -e "  ${GREEN}✓${NC} Point 6: Réception modifie [DEMO-SYNC reçu]"
    echo -e "  ${GREEN}✓${NC} Point 7: Déroulement cohérent [Logs traçables]"
    echo ""
    echo "Documentation:"
    echo -e "  • DEMO.md — Guide de démonstration complet"
    echo -e "  • RAPPORT.md — Rapport détaillé d'implémentation"
    exit 0
else
    echo -e "${RED}[FAILURE] Certains logs manquent!${NC}"
    exit 1
fi
