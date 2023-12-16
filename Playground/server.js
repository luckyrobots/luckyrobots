const http = require('http');

const server = http.createServer((req, res) => {
    if (req.method === 'POST') {
        console.log('Received a POST request');

        // Optional: Read and log the body of the POST request
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString(); // convert Buffer to string
        });
        req.on('end', () => {
            console.log('POST body:', body);
            res.end('POST request received');
        });
    } else {
        res.end('Send a POST request to log it');
    }
});

server.listen(4000, () => {
    console.log('Server listening on port 4000');
});
