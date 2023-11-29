// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#include "pipeline.h"

namespace sw {

namespace redis {

std::vector<ReplyUPtr> PipelineImpl::exec(Connection &connection, std::size_t cmd_num) {
    std::vector<ReplyUPtr> replies;
    while (cmd_num > 0) {
        replies.push_back(connection.recv(false));
        --cmd_num;
    }

    return replies;
}

}

}
