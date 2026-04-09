# Makefile — Processus C réseau (V1)
# Compilation sous Linux / WSL uniquement (POSIX shm + sémaphores)

CC      = gcc
CFLAGS  = -Wall -Wextra -g -I../shared
LDFLAGS = -lrt -lpthread

# Sources
SRCS = main.c ipc.c network.c protocol.c
OBJS = $(SRCS:.c=.o)
TARGET = c_net

# ─────────────────────────────────────────────
# Cibles
# ─────────────────────────────────────────────

all: $(TARGET) test_ipc

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "✓ Compilé : ./$(TARGET)"

test_ipc: test_ipc.o ipc.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "✓ Compilé : ./test_ipc"

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Nettoyage
clean:
	rm -f $(OBJS) test_ipc.o $(TARGET) test_ipc
	@echo "✓ Nettoyé"

# Nettoyage des ressources IPC zombies (si le process a crashé)
clean-ipc:
	-rm -f /dev/shm/battle_state
	-rm -f /dev/shm/sem.battle_sem_w
	-rm -f /dev/shm/sem.battle_sem_r
	@echo "✓ Ressources IPC supprimées"

# Lance un test standalone (sans Python)
# Crée la shm, écrit un GameState factice, le ré-affiche
test-ipc: $(TARGET)
	@echo "Test IPC : écriture puis lecture de la shm..."
	./test_ipc

.PHONY: all clean clean-ipc test-ipc
