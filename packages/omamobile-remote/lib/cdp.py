#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A small DevTools-protocol client with no dependencies (text frames only).

  cdp.py [--port N] list
  cdp.py [--port N] eval  TARGET 'JAVASCRIPT EXPRESSION'
  cdp.py [--port N] shot  TARGET OUT.png

TARGET is a piece of the page's URL or title. The port is 9222 or
$OMAMOBILE_CDP_PORT. It only ever connects to 127.0.0.1: reach a phone's
browser from another computer with `ssh -L 9222:127.0.0.1:9222 phone`.
Start the browser with omamobile-cdp first.
"""
import base64, json, os, socket, struct, sys, urllib.request

HOST = "127.0.0.1"


def targets(port):
    with urllib.request.urlopen(f"http://{HOST}:{port}/json/list", timeout=5) as r:
        return json.load(r)


class WS:
    def __init__(self, port, path):
        self.s = socket.create_connection((HOST, port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {path} HTTP/1.1\r\nHost: {HOST}:{port}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.s.recv(4096)
            if not chunk:
                raise SystemExit("cdp.py: the browser closed the connection")
            buf += chunk
        if b" 101 " not in buf.split(b"\r\n")[0]:
            raise SystemExit("cdp.py: websocket upgrade refused: " + buf.split(b"\r\n")[0].decode())
        self.rest = buf.split(b"\r\n\r\n", 1)[1]

    def send(self, text):
        data = text.encode()
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            hdr = bytes([0x81, 0x80 | n])
        elif n < 65536:
            hdr = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        while len(self.rest) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise SystemExit("cdp.py: the browser closed the connection")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def recv(self):
        msg = b""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            msg += self._read(n)
            if b1 & 0x80:
                return msg.decode()


def call(ws, method, params=None, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _id[0]:
            return m


def main(argv):
    port = int(os.environ.get("OMAMOBILE_CDP_PORT", "9222"))
    if argv[:1] == ["--port"] and len(argv) >= 2:
        port = int(argv[1])
        argv = argv[2:]
    if not argv or argv[0] not in ("list", "eval", "shot"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        pages = targets(port)
    except OSError as e:
        print(f"cdp.py: nothing on {HOST}:{port} ({e}); start omamobile-cdp, or open the ssh tunnel", file=sys.stderr)
        return 1
    if argv[0] == "list":
        for t in pages:
            print(t["type"], t["title"][:50], t["url"][:80])
        return 0
    if len(argv) < (3):
        print(__doc__, file=sys.stderr)
        return 2
    match = [t for t in pages if t["type"] == "page" and argv[1] in t["url"] + t["title"]]
    if not match:
        print(f"cdp.py: no page matches '{argv[1]}' (try: cdp.py list)", file=sys.stderr)
        return 1
    t = match[0]
    ws = WS(port, "/" + t["webSocketDebuggerUrl"].split("/", 3)[3])
    if argv[0] == "eval":
        r = call(ws, "Runtime.evaluate", {"expression": argv[2], "returnByValue": True, "awaitPromise": True})
        print(json.dumps(r.get("result", r), indent=1)[:4000])
    else:
        r = call(ws, "Page.captureScreenshot", {"format": "png"})
        with open(argv[2], "wb") as f:
            f.write(base64.b64decode(r["result"]["data"]))
        print("wrote", argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
