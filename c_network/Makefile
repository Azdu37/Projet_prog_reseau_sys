CC      = gcc
CFLAGS  = -Wall -Wextra -g -I../shared
LDFLAGS = -lrt -lpthread
SRCS    = main.c ipc.c network.c protocol.c
OBJS    = $(SRCS:.c=.o)

all: c_net test_ipc

c_net: $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

test_ipc: test_ipc.o ipc.o
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f $(OBJS) test_ipc.o c_net test_ipc

clean-ipc:
	-rm -f /dev/shm/battle_state /dev/shm/sem.battle_sem_w /dev/shm/sem.battle_sem_r

.PHONY: all clean clean-ipc
