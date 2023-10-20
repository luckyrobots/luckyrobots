// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "reply.h"
#include <cstdlib>
#include <stdexcept>

namespace sw {

namespace redis {

namespace reply {

std::string to_status(redisReply &reply) {
    if (!reply::is_status(reply)) {
        throw ProtoError("Expect STATUS reply");
    }

    if (reply.str == nullptr) {
        throw ProtoError("A null status reply");
    }

    // Old version hiredis' *redisReply::len* is of type int.
    // So we CANNOT have something like: *return {reply.str, reply.len}*.
    return std::string(reply.str, reply.len);
}

std::string parse(ParseTag<std::string>, redisReply &reply) {
    if (!reply::is_string(reply) && !reply::is_status(reply)) {
        throw ProtoError("Expect STRING reply");
    }

    if (reply.str == nullptr) {
        throw ProtoError("A null string reply");
    }

    // Old version hiredis' *redisReply::len* is of type int.
    // So we CANNOT have something like: *return {reply.str, reply.len}*.
    return std::string(reply.str, reply.len);
}

long long parse(ParseTag<long long>, redisReply &reply) {
    if (!reply::is_integer(reply)) {
        throw ProtoError("Expect INTEGER reply");
    }

    return reply.integer;
}

double parse(ParseTag<double>, redisReply &reply) {
    try {
        return std::stod(parse<std::string>(reply));
    } catch (const std::invalid_argument &) {
        throw ProtoError("not a double reply");
    } catch (const std::out_of_range &) {
        throw ProtoError("double reply out of range");
    }
}

bool parse(ParseTag<bool>, redisReply &reply) {
    auto ret = parse<long long>(reply);

    if (ret == 1) {
        return true;
    } else if (ret == 0) {
        return false;
    } else {
        throw ProtoError("Invalid bool reply: " + std::to_string(ret));
    }
}

void parse(ParseTag<void>, redisReply &reply) {
    if (!reply::is_status(reply)) {
        throw ProtoError("Expect STATUS reply");
    }

    if (reply.str == nullptr) {
        throw ProtoError("A null status reply");
    }

    static const std::string OK = "OK";

    // Old version hiredis' *redisReply::len* is of type int.
    // So we have to cast it to an unsigned int.
    if (static_cast<std::size_t>(reply.len) != OK.size()
            || OK.compare(0, OK.size(), reply.str, reply.len) != 0) {
        throw ProtoError("NOT ok status reply: " + reply::to_status(reply));
    }
}

void rewrite_set_reply(redisReply &reply) {
    if (is_nil(reply)) {
        // Failed to set, and make it a FALSE reply.
        reply.type = REDIS_REPLY_INTEGER;
        reply.integer = 0;

        return;
    }

    // Check if it's a "OK" status reply.
    reply::parse<void>(reply);

    assert(is_status(reply) && reply.str != nullptr);

    free(reply.str);

    // Make it a TRUE reply.
    reply.type = REDIS_REPLY_INTEGER;
    reply.integer = 1;
}

void rewrite_empty_array_reply(redisReply &reply) {
    if (is_array(reply) && reply.elements == 0) {
        // Make it a nil reply.
        reply.type = REDIS_REPLY_NIL;
    }
}

namespace detail {

bool is_flat_array(redisReply &reply) {
    assert(reply::is_array(reply));

    // Empty array reply.
    if (reply.element == nullptr || reply.elements == 0) {
        return false;
    }

    auto *sub_reply = reply.element[0];

    // Null element.
    if (sub_reply == nullptr) {
        return false;
    }

    return !reply::is_array(*sub_reply);
}

}

}

}

}
