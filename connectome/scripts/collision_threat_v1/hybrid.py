"""Pending circuit initiation and current image evidence, with one physical event."""
import numpy as np
from connectome.scripts.phase8.decoder import StreamingDecoder,Threshold
from connectome.scripts.behavior_validation.controllers import Controller
from .features import FeatureExtractor
from .threat_rule import ThreatRule

MODELS=('no_action','circuit','feature_only','expansion_rule','closest_approach_rule','circuit_threat_gate')

class HybridGate:
    def __init__(self):self.reset()
    def reset(self):
        self.index=0;self.pending=False;self.internal_request_ms=None
        self.physical_request_ms=None;self.fallback=False
    def update(self,k,legacy_requested,state,sustained_threat):
        if k!=self.index or not 0<=k<1000 or state not in ('unknown','threat','clear_under_model'):
            raise ValueError('Invalid hybrid clock/state')
        self.index+=1
        if legacy_requested and not self.pending:
            self.pending=True;self.internal_request_ms=float(k)
        event=False;reason=None
        if self.pending and self.physical_request_ms is None:
            if state=='unknown':
                event=True;reason='unknown_fallback';self.fallback=True
            elif state=='threat' and sustained_threat:
                event=True;reason='currently_sustained_threat'
        if event:self.physical_request_ms=float(k)
        return dict(escape_event=event,escape_requested=self.physical_request_ms is not None,
                    physical_reason=reason,fallback_event=bool(event and self.fallback),pending=self.pending)

class Driver:
    def __init__(self,model,pipeline,camera,legacy_rows):
        if model not in MODELS:raise ValueError('Unknown approved controller')
        self.model=model;self.pipeline=pipeline;self.camera=camera
        legacy_model='circuit' if model=='circuit_threat_gate' else model
        self.legacy=None;self.legacy_stream=None
        if legacy_model in ('circuit','feature_only','no_action'):
            row=legacy_rows[legacy_model]
            self.legacy=Controller(legacy_model,pipeline)
            self.legacy_stream=StreamingDecoder(Threshold(**row['threshold']),1000)
        self.rule=None;self.diagnostic=None
        if model in ('expansion_rule','closest_approach_rule','circuit_threat_gate'):
            self.rule=ThreatRule(camera,'expansion_only' if model=='expansion_rule' else 'closest_approach')
        else:self.diagnostic=FeatureExtractor(camera)
        self.gate=HybridGate() if model=='circuit_threat_gate' else None
        self.physical_request_ms=None;self.unknown_ticks=0;self.fallback_count=0
        self.latest_measurement=None;self.frame_records=[]

    def observe(self,frame,time_s):
        if self.rule:
            record=self.rule.observe(frame,time_s)
        else:
            record=dict(measurement=self.diagnostic.update(frame,time_s),estimate=None)
        self.latest_measurement=record['measurement'];self.frame_records.append(record)

    def sample(self,k,drive):
        legacy_out=None;legacy_score=None
        if self.legacy:
            legacy_score=self.legacy.score(drive)
            legacy_out=self.legacy_stream.update(float(k),legacy_score)
        rule_out=self.rule.sample(k) if self.rule else None
        if rule_out and rule_out['state']=='unknown':self.unknown_ticks+=1
        if self.gate:
            physical=self.gate.update(k,legacy_out['escape_requested'],rule_out['state'],rule_out['currently_sustained_threat'])
            self.fallback_count+=int(physical['fallback_event'])
            basis=rule_out
        elif rule_out:
            physical=dict(escape_event=rule_out['escape_event'],escape_requested=rule_out['escape_requested'],
                          physical_reason='standalone_sustained_threat' if rule_out['escape_event'] else None,
                          fallback_event=False,pending=False)
            basis=rule_out
        else:
            physical=dict(escape_event=legacy_out['escape_event'],escape_requested=legacy_out['escape_requested'],
                          physical_reason='legacy_first_event' if legacy_out['escape_event'] else None,
                          fallback_event=False,pending=False)
            basis=dict(legacy_out,score=legacy_score)
        if physical['escape_event']:
            if self.physical_request_ms is not None:raise ValueError('Repeated physical request')
            self.physical_request_ms=float(k)
        return dict(score=basis['score'],sustained_score=basis['sustained_score'],eligible=basis['eligible'],
             escape_event=physical['escape_event'],escape_requested=self.physical_request_ms is not None,
             physical_reason=physical['physical_reason'] or '',fallback_event=physical['fallback_event'],
             pending=physical['pending'],legacy_score=np.nan if legacy_score is None else legacy_score,
             legacy_sustained_score=np.nan if legacy_out is None else legacy_out['sustained_score'],
             legacy_escape_event=False if legacy_out is None else legacy_out['escape_event'],
             legacy_escape_requested=False if legacy_out is None else legacy_out['escape_requested'],
             rule_state='not_applicable' if rule_out is None else rule_out['state'],
             rule_reason='' if rule_out is None else rule_out['reason'])

    def advance(self,drive):
        if self.legacy:self.legacy.advance(drive)

    def state_vector(self):
        return self.legacy.state_vector() if self.legacy else np.empty(0,dtype=np.float64)

    @property
    def internal_request_ms(self):
        return None if self.legacy_stream is None else self.legacy_stream.first_event_ms
