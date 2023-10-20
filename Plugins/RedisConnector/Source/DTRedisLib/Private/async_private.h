// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef __HIREDIS_ASYNC_PRIVATE_H
#define __HIREDIS_ASYNC_PRIVATE_H

#define _EL_ADD_READ(ctx)                                         \
    do {                                                          \
        refreshTimeout(ctx);                                      \
        if ((ctx)->ev.addRead) (ctx)->ev.addRead((ctx)->ev.data); \
    } while (0)
#define _EL_DEL_READ(ctx) do { \
        if ((ctx)->ev.delRead) (ctx)->ev.delRead((ctx)->ev.data); \
    } while(0)
#define _EL_ADD_WRITE(ctx)                                          \
    do {                                                            \
        refreshTimeout(ctx);                                        \
        if ((ctx)->ev.addWrite) (ctx)->ev.addWrite((ctx)->ev.data); \
    } while (0)
#define _EL_DEL_WRITE(ctx) do { \
        if ((ctx)->ev.delWrite) (ctx)->ev.delWrite((ctx)->ev.data); \
    } while(0)
#define _EL_CLEANUP(ctx) do { \
        if ((ctx)->ev.cleanup) (ctx)->ev.cleanup((ctx)->ev.data); \
        ctx->ev.cleanup = NULL; \
    } while(0);

static inline void refreshTimeout(redisAsyncContext *ctx) {
    #define REDIS_TIMER_ISSET(tvp) \
        (tvp && ((tvp)->tv_sec || (tvp)->tv_usec))

    #define REDIS_EL_TIMER(ac, tvp) \
        if ((ac)->ev.scheduleTimer && REDIS_TIMER_ISSET(tvp)) { \
            (ac)->ev.scheduleTimer((ac)->ev.data, *(tvp)); \
        }

    if (ctx->c.flags & REDIS_CONNECTED) {
        REDIS_EL_TIMER(ctx, ctx->c.command_timeout);
    } else {
        REDIS_EL_TIMER(ctx, ctx->c.connect_timeout);
    }
}

void __redisAsyncDisconnect(redisAsyncContext *ac);
void redisProcessCallbacks(redisAsyncContext *ac);

#endif  /* __HIREDIS_ASYNC_PRIVATE_H */
