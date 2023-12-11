// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "shards.h"

namespace sw {

namespace redis {

RedirectionError::RedirectionError(const std::string &msg): ReplyError(msg) {
    std::tie(_slot, _node) = _parse_error(msg);
}

std::pair<Slot, Node> RedirectionError::_parse_error(const std::string &msg) const {
    // "slot ip:port"
    auto space_pos = msg.find(" ");
    auto colon_pos = msg.find(":");
    if (space_pos == std::string::npos
            || colon_pos == std::string::npos
            || colon_pos < space_pos) {
        throw ProtoError("Invalid ASK error message: " + msg);
    }

    try {
        // We need to do a cast for x86 build (32 bit) on Windows.
        auto slot = static_cast<Slot>(std::stoull(msg.substr(0, space_pos)));
        auto host = msg.substr(space_pos + 1, colon_pos - space_pos - 1);
        auto port = std::stoi(msg.substr(colon_pos + 1));

        return {slot, {host, port}};
    } catch (const std::exception &) {
        throw ProtoError("Invalid ASK error message: " + msg);
    }
}

}

}
