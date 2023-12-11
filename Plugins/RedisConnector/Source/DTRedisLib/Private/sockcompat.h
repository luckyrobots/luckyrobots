// Copyright 2022 Dexter.Wan. All Rights Reserved. 
// EMail: 45141961@qq.com

#ifndef __SOCKCOMPAT_H
#define __SOCKCOMPAT_H

#ifndef _WIN32

/* For POSIX systems we use the standard BSD socket API. */
#include <unistd.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <poll.h>

#else
/* For Windows we use winsock. */
#undef _WIN32_WINNT
#define _WIN32_WINNT 0x0600 /* To get WSAPoll etc. */

#include <winsock2.h>
#include <ws2tcpip.h>
#include <stddef.h>
#include <errno.h>

#ifdef _MSC_VER
typedef long long ssize_t;
#endif

/* Emulate the parts of the BSD socket API that we need (override the winsock signatures). */
int win32_getaddrinfo(const char *node, const char *service, const struct addrinfo *hints, struct addrinfo **res);
const char *win32_gai_strerror(int errcode);
void win32_freeaddrinfo(struct addrinfo *res);
SOCKET win32_socket(int domain, int type, int protocol);
int win32_ioctl(SOCKET fd, unsigned long request, unsigned long *argp);
int win32_bind(SOCKET sockfd, const struct sockaddr *addr, socklen_t addrlen);
int win32_connect(SOCKET sockfd, const struct sockaddr *addr, socklen_t addrlen);
int win32_getsockopt(SOCKET sockfd, int level, int optname, void *optval, socklen_t *optlen);
int win32_setsockopt(SOCKET sockfd, int level, int optname, const void *optval, socklen_t optlen);
int win32_close(SOCKET fd);
ssize_t win32_recv(SOCKET sockfd, void *buf, size_t len, int flags);
ssize_t win32_send(SOCKET sockfd, const void *buf, size_t len, int flags);
typedef ULONG nfds_t;
int win32_poll(struct pollfd *fds, nfds_t nfds, int timeout);

#ifndef REDIS_SOCKCOMPAT_IMPLEMENTATION
#define getaddrinfo(node, service, hints, res) win32_getaddrinfo(node, service, hints, res)
#undef gai_strerror
#define gai_strerror(errcode) win32_gai_strerror(errcode)
#define freeaddrinfo(res) win32_freeaddrinfo(res)
#define socket(domain, type, protocol) win32_socket(domain, type, protocol)
#define ioctl(fd, request, argp) win32_ioctl(fd, request, argp)
#define bind(sockfd, addr, addrlen) win32_bind(sockfd, addr, addrlen)
#define connect(sockfd, addr, addrlen) win32_connect(sockfd, addr, addrlen)
#define getsockopt(sockfd, level, optname, optval, optlen) win32_getsockopt(sockfd, level, optname, optval, optlen)
#define setsockopt(sockfd, level, optname, optval, optlen) win32_setsockopt(sockfd, level, optname, optval, optlen)
#define close(fd) win32_close(fd)
#define recv(sockfd, buf, len, flags) win32_recv(sockfd, buf, len, flags)
#define send(sockfd, buf, len, flags) win32_send(sockfd, buf, len, flags)
#define poll(fds, nfds, timeout) win32_poll(fds, nfds, timeout)
#endif /* REDIS_SOCKCOMPAT_IMPLEMENTATION */
#endif /* _WIN32 */

#endif /* __SOCKCOMPAT_H */
