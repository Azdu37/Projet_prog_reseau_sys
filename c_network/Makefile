CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -I. -I../shared
LDFLAGS ?=
LDLIBS ?= -pthread

TARGET := mbai_ipc_test
SRCS := main.c ipc.c
OBJS := $(SRCS:.c=.o)

.PHONY: all clean run cleanup test

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) $(LDLIBS) -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

run: $(TARGET)
	./$(TARGET)

cleanup: $(TARGET)
	./$(TARGET) cleanup

test:
	bash ../scripts/test_network.sh

clean:
	rm -f $(OBJS) $(TARGET)
