const http = require('http');
const crypto = require('crypto');

const server = http.createServer((req, res) => {
    res.writeHead(404);
    res.end();
});

server.on('upgrade', (req, socket, head) => {
    const { headers } = req;
    const acceptKey = headers['sec-websocket-key'];
    const hash = generateAcceptValue(acceptKey);

    const responseHeaders = [
        'HTTP/1.1 101 Switching Protocols',
        'Upgrade: websocket',
        'Connection: Upgrade',
        `Sec-WebSocket-Accept: ${hash}`
    ];

    socket.write(responseHeaders.join('\r\n') + '\r\n\r\n');

    console.log('Client connected');

    const sendHello = () => {
        const message = Buffer.from(JSON.stringify({'hello': 'world'}));
        const frame = Buffer.alloc(2 + message.length);
        frame.writeUInt8(0b10000001, 0); // FIN + Text frame
        frame.writeUInt8(message.length, 1); // Payload length
        message.copy(frame, 2);
        socket.write(frame);
        console.log('Sent: hello');
    };

    const interval = setInterval(sendHello, 1000);

    socket.on('close', () => {
        console.log('Client disconnected');
        clearInterval(interval);
    });
});

function generateAcceptValue(acceptKey) {
    return crypto
        .createHash('sha1')
        .update(acceptKey + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11', 'binary')
        .digest('base64');
}

server.listen(3000, () => {
    console.log('WebSocket server is running on ws://localhost:3000');
});
