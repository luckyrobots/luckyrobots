import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Global variable to store the next request
next_req = {}


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global next_req
        self.log_request("GET")
        if self.path == "/html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = f"""
            <!DOCTYPE html>
            <html>
            <body>
                <h2>Submit JSON Data</h2>
                <form action="/html" method="post">
                    <textarea name="json_data" rows="4" cols="50">{json.dumps(next_req, indent=2)}</textarea><br><br>
                    <input type="submit" value="Submit">
                </form>
                <h3>Current stored JSON:</h3>
                <pre id="storedJson">{json.dumps(next_req, indent=2)}</pre>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = json.dumps(next_req)
            self.wfile.write(response.encode())
            # Reset next_req after sending
            next_req = {}
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")
        self.log_request("POST", post_data)

        global next_req
        if self.path == "/html":
            parsed_data = parse_qs(post_data)
            json_data = parsed_data.get("json_data", ["{}"])[0]
            try:
                global next_req
                next_req = json.loads(json_data)
                self.send_response(303)  # 303 See Other
                self.send_header("Location", "/html")
                self.end_headers()
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error_message = """
                <html>
                <body>
                    <h2>Error: Invalid JSON data</h2>
                    <a href="/html">Go back to form</a>
                </body>
                </html>
                """
                self.wfile.write(error_message.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def log_request(self, method, data=None):
        logging.info(f"{method} request received:")
        logging.info(f"Path: {self.path}")
        logging.info(f"Headers: {self.headers}")
        if data:
            logging.info(f"Data: {data}")


def run_server(port=3000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Server running on port {port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
