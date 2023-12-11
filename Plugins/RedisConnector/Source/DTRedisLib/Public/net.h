// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef __NET_H
#define __NET_H

#include "hiredis.h"

#ifdef __cplusplus
extern "C" {
#endif

void redisNetClose(redisContext *c);
ssize_t redisNetRead(redisContext *c, char *buf, size_t bufcap);
ssize_t redisNetWrite(redisContext *c);

int redisCheckSocketError(redisContext *c);
int redisContextSetTimeout(redisContext *c, const struct timeval tv);
int redisContextConnectTcp(redisContext *c, const char *addr, int port, const struct timeval *timeout);
int redisContextConnectBindTcp(redisContext *c, const char *addr, int port,
                               const struct timeval *timeout,
                               const char *source_addr);
int redisContextConnectUnix(redisContext *c, const char *path, const struct timeval *timeout);
int redisKeepAlive(redisContext *c, int interval);
int redisCheckConnectDone(redisContext *c, int *completed);

int redisSetTcpNoDelay(redisContext *c);

#ifdef __cplusplus
}
#endif

#endif
