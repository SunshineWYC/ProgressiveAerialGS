"""Serve only public site files at http://127.0.0.1:8000/ (Python 3.9+)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / 'site'
handler = partial(SimpleHTTPRequestHandler, directory=str(root))
try:
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
except OSError as error:
    parser.exit(1, 'Cannot start preview: {}. Try --port 8001.\n'.format(error))
print('Preview: http://127.0.0.1:{}/  (serving site/ only; Ctrl+C to stop)'.format(args.port), flush=True)
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
