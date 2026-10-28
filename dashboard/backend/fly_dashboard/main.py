"""HTTP/WS presentation service. No scientific execution routes or model imports."""
import asyncio
from contextlib import asynccontextmanager
import json
import secrets
from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from .config import Settings
from .repository import Repository
from .live import LiveSpec, LiveFrame, TelemetryHub

def create_app(settings: Settings | None = None):
    settings=settings or Settings.environment()
    repo=Repository(settings);hub=TelemetryHub()
    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(repo.refresh)
        yield
        # Only in-memory caches exist; no scientific files to publish on exit.
    app=FastAPI(title='FLY Observatory',version='1.2.0',lifespan=lifespan)
    app.state.repository=repo;app.state.hub=hub
    app.add_middleware(CORSMiddleware,allow_origins=list(settings.origins),allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','X-Fly-Ingest-Token'])
    app.add_middleware(GZipMiddleware,minimum_size=1024)

    @app.middleware('http')
    async def revalidate_dashboard(request,call_next):
        response=await call_next(request)
        if request.url.path in ('/','/index.html'):
            response.headers['Cache-Control']='no-store'
        return response

    def require_producer(x_fly_ingest_token: str = Header(default='')):
        if not settings.ingest_token or not secrets.compare_digest(x_fly_ingest_token,settings.ingest_token):
            raise HTTPException(403,'Producer ingestion is disabled or the token is invalid')

    def load(ident):
        try:return repo.load(ident)
        except KeyError:raise HTTPException(404,'Episode not found; refresh the saved catalog')
        except (ValueError,OSError,IndexError,TypeError) as error:raise HTTPException(409,f'Saved artifact rejected: {error}')

    @app.get('/api/v1/health')
    def health():
        return dict(status='ok',api_version='1.2.0',telemetry_schema='live_telemetry_1.2',body_orientation=True,surround_rgb=True,world_dimensions=[2,3],separate_signal_timestamps=True,frontend_ready=(settings.project_root/'dashboard/frontend/dist/index.html').is_file(),scientific_access='read_only',experiment_execution=False,
                    producer_ingestion=bool(settings.ingest_token),supported_modes=['verified_replay','live_artifact_discovery','external_live_telemetry'])

    @app.get('/api/v1/catalog')
    def catalog():return repo.refresh()

    @app.get('/api/v1/status')
    def status():return repo.status()

    @app.get('/api/v1/connectome')
    def connectome():return repo.graph()

    @app.get('/api/v1/episodes/{ident}/replay')
    def replay(ident: str):return load(ident)['payload']

    @app.get('/api/v1/episodes/{ident}/camera.png')
    def camera(ident: str):
        value=load(ident)
        return Response(value['camera_png'],media_type='image/png',headers={'Cache-Control':'private, max-age=3600','ETag':value['payload']['integrity']['sha256']})

    @app.post('/api/v1/producer/check',dependencies=[Depends(require_producer)])
    async def producer_check(spec: LiveSpec):
        sessions=await hub.catalog()
        return dict(authenticated=True,schema_valid=True,world_dimension=spec.world_config.get('world_dimension',2),
                    available_sessions=max(0,4-len(sessions)),max_sensor_views=6,creates_session=False,experiment_execution=False)

    @app.get('/api/v1/live')
    async def live_catalog():return dict(sessions=await hub.catalog(),ingestion_enabled=bool(settings.ingest_token))

    @app.post('/api/v1/live',dependencies=[Depends(require_producer)])
    async def live_create(spec: LiveSpec):
        try:return await hub.create(spec)
        except ValueError as error:raise HTTPException(409,str(error))

    @app.post('/api/v1/live/{ident}/frames',dependencies=[Depends(require_producer)])
    async def live_frame(ident: str,frame: LiveFrame):
        if frame.neural_kind == 'anatomical' and set(frame.neural_ids) != {n['id'] for n in repo.graph()['nodes']}:
            raise HTTPException(409,'Anatomical telemetry IDs differ from Circuit v2')
        try:await hub.publish(ident,frame)
        except KeyError:raise HTTPException(404,'Unknown live session')
        except ValueError as error:raise HTTPException(409,str(error))
        return dict(accepted=True,time_ms=frame.time_ms)

    @app.post('/api/v1/live/{ident}/end',dependencies=[Depends(require_producer)])
    async def live_end(ident: str):
        try:await hub.end(ident)
        except KeyError:raise HTTPException(404,'Unknown live session')
        return dict(ended=True)

    @app.delete('/api/v1/live/{ident}',dependencies=[Depends(require_producer)])
    async def live_remove(ident: str):
        try:await hub.remove(ident)
        except KeyError:raise HTTPException(404,'Unknown live session')
        except ValueError as error:raise HTTPException(409,str(error))
        return dict(removed=True)

    async def accept_viewer(ws):
        origin=ws.headers.get('origin')
        if origin and origin not in settings.origins:
            await ws.close(code=1008);return False
        await ws.accept();return True

    @app.websocket('/api/v1/catalog/ws')
    async def catalog_watch(ws: WebSocket):
        if not await accept_viewer(ws):return
        signature=None
        try:
            while True:
                data=await run_in_threadpool(repo.refresh)
                current=json.dumps(data,sort_keys=True)
                if current!=signature:
                    await ws.send_json(dict(type='catalog',catalog=data));signature=current
                else:await ws.send_json(dict(type='heartbeat'))
                await asyncio.sleep(3)
        except (WebSocketDisconnect,RuntimeError):return

    @app.websocket('/api/v1/live/{ident}/ws')
    async def live_watch(ws: WebSocket,ident: str):
        if not await accept_viewer(ws):return
        queue=None
        try:
            queue,snapshot=await hub.subscribe(ident)
            await ws.send_json(snapshot)
            while True:
                try:message=await asyncio.wait_for(queue.get(),timeout=15)
                except asyncio.TimeoutError:message=dict(type='heartbeat')
                await ws.send_json(message)
                if message.get('type') == 'ended':break
                if message.get('type') == 'frame': await asyncio.sleep(1/30)
        except KeyError:await ws.close(code=1008,reason='Unknown session')
        except (WebSocketDisconnect,RuntimeError):pass
        finally:
            if queue is not None:await hub.unsubscribe(ident,queue)
    built = settings.project_root / 'dashboard/frontend/dist'
    if built.is_dir(): app.mount('/',StaticFiles(directory=str(built),html=True),name='observatory')
    return app

app=create_app()
