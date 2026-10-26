"""Minimal *experimental* single-job local inference API. Not internet-safe without an API token.
Dependencies fastapi/uvicorn/python-multipart must be included in upstream venv at setup.
"""
import os, subprocess, time, uuid, threading, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import FileResponse
import uvicorn

ROOT=Path('/opt/kandinsky-6')
DATA=Path('/workspace/jobs'); DATA.mkdir(parents=True,exist_ok=True)
TOKEN=os.environ.get('SYNTHETIC_API_TOKEN','')
if not TOKEN:
    raise RuntimeError('Set SYNTHETIC_API_TOKEN before starting the API; do not expose publicly without auth')
app=FastAPI(title='Synthetic Muse experimental Kandinsky worker')
lock=threading.Lock()
state={}

def auth(authorization):
    if authorization != f'Bearer {TOKEN}': raise HTTPException(401,'Unauthorized')

@app.get('/health')
def health(): return {'status':'ready','model':'kandinsky-6.0-lite-distill','gpu':'RTX 4090 expected','mode':'test-only'}

@app.post('/generate')
async def generate(prompt: str=Form(...), image:UploadFile=File(...), authorization: str|None=Header(default=None)):
    auth(authorization)
    if not prompt.strip() or len(prompt)>6000: raise HTTPException(400,'Prompt length invalid')
    if not image.filename or not image.filename.lower().endswith(('.png','.jpg','.jpeg')):
        raise HTTPException(400,'Upload PNG/JPG image')
    if not lock.acquire(blocking=False): raise HTTPException(429,'Worker busy; one generation at a time')
    jobid=str(uuid.uuid4()); folder=DATA/jobid; folder.mkdir()
    content=await image.read(15_000_001)
    if len(content)>15_000_000:
        lock.release(); raise HTTPException(413,'Image too large')
    input_image=folder/'first.png'
    from PIL import Image
    from io import BytesIO
    try:
        im=Image.open(BytesIO(content)).convert('RGB')
        im.save(input_image)
    except Exception:
        lock.release(); raise HTTPException(400,'Invalid image')
    state[jobid]={'status':'running','start':time.time()}
    def work():
        try:
            cmd=['just','generate',prompt,'--config','/tmp/synthetic-lite-4090.yaml','--image',str(input_image),'--out',str(folder/'result.mp4')]
            start=time.monotonic()
            with open(folder/'run.log','w') as log:
                p=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=2400)
            state[jobid]={'status':'completed' if p.returncode==0 and (folder/'result.mp4').exists() else 'failed','elapsed_seconds':round(time.monotonic()-start,1),'exit_code':p.returncode}
        except Exception as e: state[jobid]={'status':'failed','message':str(e)}
        finally: lock.release()
    threading.Thread(target=work,daemon=True).start()
    return {'job_id':jobid,'status':'running'}

@app.get('/jobs/{jobid}')
def status(jobid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    if jobid not in state: raise HTTPException(404,'Job missing')
    return state[jobid]

@app.get('/jobs/{jobid}/video')
def video(jobid:str,authorization:str|None=Header(default=None)):
    auth(authorization)
    if jobid not in state or state[jobid]['status']!='completed': raise HTTPException(404,'Output unavailable')
    return FileResponse(DATA/jobid/'result.mp4',media_type='video/mp4',filename=f'{jobid}.mp4')

if __name__=='__main__':
    uvicorn.run(app,host='0.0.0.0',port=8000)
