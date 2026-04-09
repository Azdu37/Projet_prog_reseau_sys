CC      = gcc
CFLAGS  = -Wall -Wextra -std=gnu99 -pthread -O2 -I../shared
LDFLAGS = -lpthread
SRC     = main.c network.c ipc_local.c protocol.c
OBJ     = $(SRC:.c=.o)

all: build/network

build/network: $(OBJ)
	mkdir -p build
	$(CC) $(OBJ) -o $@ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) build/network
