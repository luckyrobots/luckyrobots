// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef SEWENEW_REDISPLUSPLUS_NO_TLS_H
#define SEWENEW_REDISPLUSPLUS_NO_TLS_H

#include "hiredis.h"

namespace sw {

namespace redis {

namespace tls {

struct TlsOptions {};

struct TlsContextUPtr {};

inline TlsContextUPtr secure_connection(redisContext &/*ctx*/, const TlsOptions &/*opts*/) {
    // Do nothing
    return {};
}

inline bool enabled(const TlsOptions &/*opts*/) {
    return false;
}

}

}

}

#endif // end SEWENEW_REDISPLUSPLUS_NO_TLS_H
