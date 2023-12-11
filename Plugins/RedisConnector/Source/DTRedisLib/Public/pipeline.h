// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef SEWENEW_REDISPLUSPLUS_PIPELINE_H
#define SEWENEW_REDISPLUSPLUS_PIPELINE_H

#include <cassert>
#include <vector>
#include "connection.h"

namespace sw {

namespace redis {

class PipelineImpl {
public:
    template <typename Cmd, typename ...Args>
    void command(Connection &connection, Cmd cmd, Args &&...args) {
        assert(!connection.broken());

        cmd(connection, std::forward<Args>(args)...);
    }

    std::vector<ReplyUPtr> exec(Connection &connection, std::size_t cmd_num);

    void discard(Connection &connection, std::size_t /*cmd_num*/) {
        // Reconnect to Redis to discard all commands.
        connection.reconnect();
    }
};

}

}

#endif // end SEWENEW_REDISPLUSPLUS_PIPELINE_H
