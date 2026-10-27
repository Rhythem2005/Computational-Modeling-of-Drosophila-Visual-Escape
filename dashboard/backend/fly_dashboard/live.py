"""Bounded optional producer telemetry. Never starts an experiment or writes science files."""
import asyncio
import base64
from collections import deque
import math
import struct
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

class LiveSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=120)
    protocol: str = Field(min_length=1, max_length=160)
    controller: str = Field(min_length=1, max_length=160)
    source_note: str = Field(min_length=1, max_length=500)
    world_config: dict[str, Any]

    @model_validator(mode='after')
    def world_contract(self):
        dimension=self.world_config.get('world_dimension',2)
        if type(dimension) is not int or dimension not in (2,3):raise ValueError('Unsupported physical dimensions')
        radius = self.world_config.get('fly_radius')
        if not isinstance(radius, (int, float)) or isinstance(radius, bool) or not math.isfinite(radius) or radius <= 0:
            raise ValueError('Producer must declare its actual fly_radius')
        # Reject NaN/Infinity anywhere in the supplied config.
        import json
        json.dumps(self.world_config, allow_nan=False)
        return self

class Obstacle(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1, max_length=80)
    position: list[FiniteFloat] = Field(min_length=2, max_length=3)
    radius: FiniteFloat = Field(gt=0)

class LiveEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    time_ms: FiniteFloat = Field(ge=0)
    kind: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=160)

class LiveFrame(BaseModel):
    model_config = ConfigDict(extra='forbid')
    time_ms: FiniteFloat = Field(ge=0)
    fly: list[FiniteFloat] = Field(min_length=2, max_length=3)
    obstacles: list[Obstacle] = Field(max_length=64)
    decision_timestamp_ms: FiniteFloat | None = Field(default=None, ge=0)
    neural_timestamp_ms: FiniteFloat | None = Field(default=None, ge=0)
    speed: FiniteFloat | None = None
    score: FiniteFloat | None = None
    sustained_score: FiniteFloat | None = None
    gate_state: str | None = Field(default=None, max_length=80)
    rule_state: str | None = Field(default=None, max_length=80)
    encoder_channels: list[FiniteFloat] | None = Field(default=None, min_length=2, max_length=2)
    encoder_drive: list[FiniteFloat] | None = Field(default=None, min_length=321, max_length=321)
    encoder_body_ids: list[int] = Field(default_factory=list, max_length=321)
    encoder_valid: bool | None = None
    neural_kind: Literal['anatomical', 'gru_hidden', 'unavailable'] = 'unavailable'
    neural_ids: list[int | str] = Field(default_factory=list, max_length=512)
    neural_values: list[FiniteFloat] = Field(default_factory=list, max_length=512)
    camera_timestamp_ms: FiniteFloat | None = Field(default=None, ge=0)
    camera_png_base64: str | None = Field(default=None, max_length=262144)
    events: list[LiveEvent] = Field(default_factory=list, max_length=16)

    @model_validator(mode='after')
    def causal_dimensions(self):
        if any(len(o.position)!=len(self.fly) for o in self.obstacles):raise ValueError('Mixed world dimensions')
        if any(t is not None and t>self.time_ms for t in (self.decision_timestamp_ms,self.neural_timestamp_ms)):raise ValueError('Future neural/decision timestamp')
        if len(self.neural_ids) != len(self.neural_values): raise ValueError('State IDs and values must align')
        if len(set(self.neural_ids)) != len(self.neural_ids): raise ValueError('Duplicate neural IDs')
        if self.encoder_drive is not None and (len(self.encoder_body_ids)!=321 or len(set(self.encoder_body_ids))!=321):
            raise ValueError('Encoder drive requires 321 ordered unique body IDs')
        expected = {'anatomical':321, 'gru_hidden':16, 'unavailable':0}[self.neural_kind]
        if len(self.neural_values) != expected: raise ValueError('State width does not match its declared kind')
        if self.camera_timestamp_ms is not None and self.camera_timestamp_ms > self.time_ms:
            raise ValueError('Camera observation is in the future')
        if any(e.time_ms > self.time_ms for e in self.events): raise ValueError('Event is in the future')
        if self.camera_png_base64:
            image = base64.b64decode(self.camera_png_base64, validate=True)
            if len(image)<24 or image[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('Expected PNG')
            w,h=struct.unpack('!II',image[16:24])
            if not 1<=w<=512 or not 1<=h<=512: raise ValueError('Telemetry camera dimensions exceed 512')
            if self.camera_timestamp_ms is None: raise ValueError('Camera timestamp is required with an image')
        return self

class TelemetryHub:
    def __init__(self):
        self.sessions = {}
        self.lock = asyncio.Lock()

    async def create(self, spec: LiveSpec):
        async with self.lock:
            if len(self.sessions)>=4: raise ValueError('Four-session limit reached; remove an ended session')
            ident=uuid4().hex
            self.sessions[ident]=dict(spec=spec.model_dump(), frames=deque(maxlen=200), listeners=set(), active=True)
            return dict(id=ident, **self.sessions[ident]['spec'], active=True, verification='external_producer_unverified')

    async def catalog(self):
        async with self.lock:
            return [dict(id=k, **v['spec'], active=v['active'], frame_count=len(v['frames']),
                         last_time_ms=v['frames'][-1]['time_ms'] if v['frames'] else None,
                         verification='external_producer_unverified') for k,v in self.sessions.items()]

    async def publish(self, ident, frame: LiveFrame):
        async with self.lock:
            session=self.sessions[ident]
            if not session['active']: raise ValueError('Session has ended')
            dimension=session['spec']['world_config'].get('world_dimension',2)
            if len(frame.fly)!=dimension:raise ValueError('Frame dimensions differ from the session')
            value=frame.model_dump()
            if session['frames']:
                previous=session['frames'][-1]
                if value['time_ms']<=previous['time_ms']: raise ValueError('Time must increase; use a new session for reset')
                if [(o['id'],o['radius']) for o in value['obstacles']] != [(o['id'],o['radius']) for o in previous['obstacles']]:
                    raise ValueError('Object identities/radii changed; use a new session')
                if (value['neural_kind'],value['neural_ids']) != (previous['neural_kind'],previous['neural_ids']):
                    raise ValueError('State identity changed; use a new session')
            session['frames'].append(value)
            for queue in tuple(session['listeners']):
                if queue.full(): queue.get_nowait()
                queue.put_nowait(dict(type='frame', frame=value))

    async def subscribe(self, ident):
        async with self.lock:
            session=self.sessions[ident];queue=asyncio.Queue(maxsize=2)
            session['listeners'].add(queue)
            return queue,dict(type='snapshot', session=dict(id=ident,**session['spec'],active=session['active']),
                              frames=list(session['frames']))

    async def unsubscribe(self, ident, queue):
        async with self.lock:
            if ident in self.sessions:self.sessions[ident]['listeners'].discard(queue)

    async def end(self, ident):
        async with self.lock:
            session=self.sessions[ident];session['active']=False
            for queue in session['listeners']:
                if queue.full():queue.get_nowait()
                queue.put_nowait(dict(type='ended'))

    async def remove(self, ident):
        async with self.lock:
            session=self.sessions[ident]
            if session['active'] or session['listeners']: raise ValueError('End session and detach viewers first')
            del self.sessions[ident]
