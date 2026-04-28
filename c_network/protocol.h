#ifndef PROTOCOL_NET_H
#define PROTOCOL_NET_H

#include "../shared/protocol.h"

void proto_handle_incoming(const NetMessage *msg, GameState *state);

#endif
