// Ce fichier gère la mémoire partagée et les sémaphores pour la communication inter-processus (IPC).
// Il permet de lire et d'écrire l'état du jeu pour le partager entre les différents composants.

#include "ipc.h"
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <semaphore.h>
#include <unistd.h>

static GameState *g_shm   = NULL;
static int        g_fd    = -1;
static sem_t     *g_sem_w = NULL;
static sem_t     *g_sem_r = NULL;
static int        g_owner = 0;
static char       g_names[3][64];

int ipc_init(const char *shm_name, const char *sem_w, const char *sem_r, int create)
{
    if (create) { shm_unlink(shm_name); sem_unlink(sem_w); sem_unlink(sem_r); }

    g_fd = shm_open(shm_name, O_RDWR | (create ? O_CREAT : 0), 0666);
    if (g_fd < 0) { perror("shm_open"); return -1; }

    if (create && ftruncate(g_fd, sizeof(GameState)) < 0) {
        perror("ftruncate"); close(g_fd); return -1;
    }

    g_shm = mmap(NULL, sizeof(GameState), PROT_READ|PROT_WRITE, MAP_SHARED, g_fd, 0);
    if (g_shm == MAP_FAILED) { perror("mmap"); close(g_fd); return -1; }

    if (create) {
        memset(g_shm, 0, sizeof(GameState));
        g_shm->magic = PROTOCOL_MAGIC;
        g_shm->version = PROTOCOL_VERSION;
    }

    int sf = create ? O_CREAT : 0;
    g_sem_w = sem_open(sem_w, sf, 0666, 1);
    g_sem_r = sem_open(sem_r, sf, 0666, 1);
    if (g_sem_w == SEM_FAILED || g_sem_r == SEM_FAILED) {
        perror("sem_open"); return -1;
    }

    strncpy(g_names[0], shm_name, 63);
    strncpy(g_names[1], sem_w, 63);
    strncpy(g_names[2], sem_r, 63);
    g_owner = create;
    return 0;
}

int ipc_read_state(GameState *out)
{
    if (!g_shm || !g_sem_w) return -1;
    sem_wait(g_sem_w);
    memcpy(out, g_shm, sizeof(GameState));
    sem_post(g_sem_w);
    return 0;
}

int ipc_write_state(const GameState *in)
{
    if (!g_shm || !g_sem_w) return -1;
    sem_wait(g_sem_w);
    memcpy(g_shm, in, sizeof(GameState));
    sem_post(g_sem_w);
    return 0;
}

void ipc_close(void)
{
    if (g_shm && g_shm != MAP_FAILED) munmap(g_shm, sizeof(GameState));
    if (g_fd >= 0) close(g_fd);
    if (g_sem_w && g_sem_w != SEM_FAILED) sem_close(g_sem_w);
    if (g_sem_r && g_sem_r != SEM_FAILED) sem_close(g_sem_r);
    g_shm = NULL; g_fd = -1; g_sem_w = NULL; g_sem_r = NULL;

    if (g_owner) {
        shm_unlink(g_names[0]);
        sem_unlink(g_names[1]);
        sem_unlink(g_names[2]);
    }
}
