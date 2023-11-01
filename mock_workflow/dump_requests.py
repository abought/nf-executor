#!/usr/bin/env python3

"""
Quick and dirty debug tool: Log all inbound HTTP requests to the terminal
https://unix.stackexchange.com/questions/57938/generic-http-server-that-just-dumps-post-requests
"""

import argparse
import http.server
import json
import sys


class Dumper(http.server.BaseHTTPRequestHandler):
    def do_GET(self, method='GET'):
        print(f'\n{method} {self.path}\n{self.headers}')
        self.send_response(200)
        self.end_headers()

    def do_DELETE(self):
        return self.do_GET('DELETE')

    def do_POST(self, method='POST'):
        """If this receives many separate requests, """
        n = int(self.headers.get('content-length', 0))
        body = self.rfile.read(n)
        # print('{body}')
        ct = self.headers.get('content-type') or self.headers.get('Content-Type')
        if ct == 'application/json':
            d = json.loads(body)
            # One line of JSON per record: roughly same effect as a jsonl document
            print(json.dumps(d, sort_keys=True))
        else:
            print(body)


        self.send_response(200)
        self.end_headers()

    def do_PUT(self):
        return self.do_POST('PUT')

    def log_message(self, format, *args):
        pass


def main():
    p = argparse.ArgumentParser(description='Dump HTTP requests to stdout')
    p.add_argument('-a', '--address', help='bind address', default='localhost')
    p.add_argument('-p', '--port', type=int, help='bind port', default=8888)
    xs = p.parse_args()
    s = http.server.HTTPServer((xs.address, xs.port), Dumper)

    s.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
