// Ce fichier définit les fonctions et les structures nécessaires pour la communication inter-processus (IPC).
// Il déclare les fonctions d'initialisation, de fermeture, de lecture et d'écriture de l'état du jeu.

#ifndef IPC_H
#define IPC_H

#include "../shared/protocol.h"

int  ipc_init(const char *shm_name, const char *sem_w, const char *sem_r, int create);
void ipc_close(void);
int  ipc_read_state(GameState *out);
int  ipc_write_state(const GameState *in);

#endif
