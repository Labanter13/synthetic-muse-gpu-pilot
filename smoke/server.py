"""Harmless read-only GPU deployment diagnostic endpoint; no generation."""
import json
import os
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def probe():
    result={"service":"synthetic-muse-gpu-smoke","status":"running", "gpu_visible":False}
    result["free_disk_gb"]=round(shutil.disk_usage('/').free/1024**3,2)
    try:
        x=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total','--format=csv,noheader'],capture_output=True,text=True,timeout=8)
        if x.returncode == 0 and x.stdout.strip():
            result['gpu_visible']=True
            result['gpu_details']=x.stdout.strip().splitlines()[:4]
        else:
            result['gpu_diagnostic']=(x.stderr or 'nvidia-smi did not return GPU information')[:180]
    except (OSError, subprocess.TimeoutExpired) as e:
        result['gpu_diagnostic']=str(e)[:180]
    return result

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/','/health','/gpu'):
            self.send_response(404);self.end_headers();return
        b=json.dumps(probe(),ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(b)))
        self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(b)
    def log_message(self,fmt,*args):
        print(fmt%args,flush=True)

def emit_gpu_diagnostics():
    # Prints to standard container logs, so SSH / the browser terminal is not required.
    for attempt in range(1, 4):
        try:
            print("GPU_CHECK " + json.dumps({"attempt": attempt, **probe()}, ensure_ascii=False), flush=True)
        except Exception as exc:
            print("GPU_CHECK_ERROR " + str(exc), flush=True)
        if attempt != 3:
            time.sleep(10)

if __name__=='__main__':
    port=int(os.environ.get('PORT','8000'))
    print('GPU smoke server listening on port',port,flush=True)
    threading.Thread(target=emit_gpu_diagnostics, daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
