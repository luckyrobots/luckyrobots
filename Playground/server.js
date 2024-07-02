const http = require('http');
let i=0;
const server = http.createServer((req, res) => {
    if (req.method === 'POST') {
        console.log('Received a POST request');

        // Optional: Read and log the body of the POST request
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString(); // convert Buffer to string
        });
        req.on('end', () => {
            console.log(i++, " POST body:", body);
            res.end('POST request received');
        });
    }else if(req.method === 'GET'){

        const url = new URL(req.url, `http://${req.headers.host}`);
        if (url.searchParams.toString().length >0){
            console.log(i++, 'GET parameters:', url.searchParams.toString());
        }
        else{
            console.i++
        }
        randomCommand = ""
        // const commands = [
        //     ["m1 8000 1", "m2 8000 1","m3 8000 1","m4 8000 1"],
        //     "a 30 1", 
        //     "a 0 1",
        //     "m1 0 0", 
        //     "d 30 1"];
        // const randomCommand = commands[Math.floor(Math.random() * commands.length)];
        // console.log(i, 'Random command selected:', randomCommand);

        res.end(randomCommand);

    } else {
        res.end('Send a POST request to log it');
    }
});

server.listen(3000, () => {
    console.log('Server listening on port 3000');
}); 