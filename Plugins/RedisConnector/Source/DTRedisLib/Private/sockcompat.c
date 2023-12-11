// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#define REDIS_SOCKCOMPAT_IMPLEMENTATION
#include "sockcompat.h"

#ifdef _WIN32
static int _wsaErrorToErrno(int err) {
    switch (err) {
        case WSAEWOULDBLOCK:
            return EWOULDBLOCK;
        case WSAEINPROGRESS:
            return EINPROGRESS;
        case WSAEALREADY:
            return EALREADY;
        case WSAENOTSOCK:
            return ENOTSOCK;
        case WSAEDESTADDRREQ:
            return EDESTADDRREQ;
        case WSAEMSGSIZE:
            return EMSGSIZE;
        case WSAEPROTOTYPE:
            return EPROTOTYPE;
        case WSAENOPROTOOPT:
            return ENOPROTOOPT;
        case WSAEPROTONOSUPPORT:
            return EPROTONOSUPPORT;
        case WSAEOPNOTSUPP:
            return EOPNOTSUPP;
        case WSAEAFNOSUPPORT:
            return EAFNOSUPPORT;
        case WSAEADDRINUSE:
            return EADDRINUSE;
        case WSAEADDRNOTAVAIL:
            return EADDRNOTAVAIL;
        case WSAENETDOWN:
            return ENETDOWN;
        case WSAENETUNREACH:
            return ENETUNREACH;
        case WSAENETRESET:
            return ENETRESET;
        case WSAECONNABORTED:
            return ECONNABORTED;
        case WSAECONNRESET:
            return ECONNRESET;
        case WSAENOBUFS:
            return ENOBUFS;
        case WSAEISCONN:
            return EISCONN;
        case WSAENOTCONN:
            return ENOTCONN;
        case WSAETIMEDOUT:
            return ETIMEDOUT;
        case WSAECONNREFUSED:
            return ECONNREFUSED;
        case WSAELOOP:
            return ELOOP;
        case WSAENAMETOOLONG:
            return ENAMETOOLONG;
        case WSAEHOSTUNREACH:
            return EHOSTUNREACH;
        case WSAENOTEMPTY:
            return ENOTEMPTY;
        default:
            /* We just return a generic I/O error if we could not find a relevant error. */
            return EIO;
    }
}

static void _updateErrno(int success) {
    errno = success ? 0 : _wsaErrorToErrno(WSAGetLastError());
}

static int _initWinsock() {
    static int s_initialized = 0;
    if (!s_initialized) {
        static WSADATA wsadata;
        int err = WSAStartup(MAKEWORD(2,2), &wsadata);
        if (err != 0) {
            errno = _wsaErrorToErrno(err);
            return 0;
        }
        s_initialized = 1;
    }
    return 1;
}

int win32_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints, struct addrinfo **res) {
    /* Note: This function is likely to be called before other functions, so run init here. */
    if (!_initWinsock()) {
        return EAI_FAIL;
    }

    switch (getaddrinfo(node, service, hints, res)) {
        case 0:                     return 0;
        case WSATRY_AGAIN:          return EAI_AGAIN;
        case WSAEINVAL:             return EAI_BADFLAGS;
        case WSAEAFNOSUPPORT:       return EAI_FAMILY;
        case WSA_NOT_ENOUGH_MEMORY: return EAI_MEMORY;
        case WSAHOST_NOT_FOUND:     return EAI_NONAME;
        case WSATYPE_NOT_FOUND:     return EAI_SERVICE;
        case WSAESOCKTNOSUPPORT:    return EAI_SOCKTYPE;
        default:                    return EAI_FAIL;     /* Including WSANO_RECOVERY */
    }
}

const char *win32_gai_strerror(int errcode) {
    switch (errcode) {
        case 0:            errcode = 0;                     break;
        case EAI_AGAIN:    errcode = WSATRY_AGAIN;          break;
        case EAI_BADFLAGS: errcode = WSAEINVAL;             break;
        case EAI_FAMILY:   errcode = WSAEAFNOSUPPORT;       break;
        case EAI_MEMORY:   errcode = WSA_NOT_ENOUGH_MEMORY; break;
        case EAI_NONAME:   errcode = WSAHOST_NOT_FOUND;     break;
        case EAI_SERVICE:  errcode = WSATYPE_NOT_FOUND;     break;
        case EAI_SOCKTYPE: errcode = WSAESOCKTNOSUPPORT;    break;
        default:           errcode = WSANO_RECOVERY;        break; /* Including EAI_FAIL */
    }
    return gai_strerror(errcode);
}

void win32_freeaddrinfo(struct addrinfo *res) {
    freeaddrinfo(res);
}

SOCKET win32_socket(int domain, int type, int protocol) {
    SOCKET s;

    /* Note: This function is likely to be called before other functions, so run init here. */
    if (!_initWinsock()) {
        return INVALID_SOCKET;
    }

    _updateErrno((s = socket(domain, type, protocol)) != INVALID_SOCKET);
    return s;
}

int win32_ioctl(SOCKET fd, unsigned long request, unsigned long *argp) {
    int ret = ioctlsocket(fd, (long)request, argp);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_bind(SOCKET sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    int ret = bind(sockfd, addr, addrlen);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_connect(SOCKET sockfd, const struct sockaddr *addr, socklen_t addrlen) {
    int ret = connect(sockfd, addr, addrlen);
    _updateErrno(ret != SOCKET_ERROR);

    /* For Winsock connect(), the WSAEWOULDBLOCK error means the same thing as
     * EINPROGRESS for POSIX connect(), so we do that translation to keep POSIX
     * logic consistent. */
    if (errno == EWOULDBLOCK) {
        errno = EINPROGRESS;
    }

    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_getsockopt(SOCKET sockfd, int level, int optname, void *optval, socklen_t *optlen) {
    int ret = 0;
    if ((level == SOL_SOCKET) && ((optname == SO_RCVTIMEO) || (optname == SO_SNDTIMEO))) {
        if (*optlen >= sizeof (struct timeval)) {
            struct timeval *tv = optval;
            DWORD timeout = 0;
            socklen_t dwlen = 0;
            ret = getsockopt(sockfd, level, optname, (char *)&timeout, &dwlen);
            tv->tv_sec = timeout / 1000;
            tv->tv_usec = (timeout * 1000) % 1000000;
        } else {
            ret = WSAEFAULT;
        }
        *optlen = sizeof (struct timeval);
    } else {
        ret = getsockopt(sockfd, level, optname, (char*)optval, optlen);
    }
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_setsockopt(SOCKET sockfd, int level, int optname, const void *optval, socklen_t optlen) {
    int ret = 0;
    if ((level == SOL_SOCKET) && ((optname == SO_RCVTIMEO) || (optname == SO_SNDTIMEO))) {
        const struct timeval *tv = optval;
        DWORD timeout = tv->tv_sec * 1000 + tv->tv_usec / 1000;
        ret = setsockopt(sockfd, level, optname, (const char*)&timeout, sizeof(DWORD));
    } else {
        ret = setsockopt(sockfd, level, optname, (const char*)optval, optlen);
    }
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_close(SOCKET fd) {
    int ret = closesocket(fd);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

ssize_t win32_recv(SOCKET sockfd, void *buf, size_t len, int flags) {
    int ret = recv(sockfd, (char*)buf, (int)len, flags);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

ssize_t win32_send(SOCKET sockfd, const void *buf, size_t len, int flags) {
    int ret = send(sockfd, (const char*)buf, (int)len, flags);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}

int win32_poll(struct pollfd *fds, nfds_t nfds, int timeout) {
    int ret = WSAPoll(fds, nfds, timeout);
    _updateErrno(ret != SOCKET_ERROR);
    return ret != SOCKET_ERROR ? ret : -1;
}
#endif /* _WIN32 */
