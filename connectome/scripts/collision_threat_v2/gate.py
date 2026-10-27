"""Circuit-armed, evidence-aware retirement; no learned timeout or re-aiming."""
from connectome.scripts.phase8.decoder import StreamingDecoder,Threshold

class RetirementGate:
    def __init__(self):self.reset()

    def reset(self):
        self.index=0;self.phase='unarmed';self.armed=False;self.epoch=0
        self.internal_request_ms=None;self.physical_request_ms=None;self.last_retired_ms=None
        self.generations=[];self.retirements=[];self.rearms=[];self.fallback=False
        self.threat=StreamingDecoder(Threshold('finite',1.),1000)
        self.clear=StreamingDecoder(Threshold('finite',1.),1000)

    def update(self,k,legacy_requested,state):
        if type(k) is not int or k!=self.index or not 0<=k<1000:
            raise ValueError('Invalid retirement gate clock')
        if state not in ('unknown','threat','clear_under_model') or not isinstance(legacy_requested,bool):
            raise ValueError('Invalid retirement gate evidence')
        self.index+=1
        t=self.threat.update(float(k),float(state=='threat'))
        c=self.clear.update(float(k),float(state=='clear_under_model'))
        threat_now=bool(t['eligible'] and t['sustained_score']>=1)
        clear_now=bool(c['eligible'] and c['sustained_score']>=1)
        generated=retired=rearmed=event=fallback=False;reason=''
        if legacy_requested and not self.armed:
            self.armed=True;self.internal_request_ms=float(k);self.phase='pending';self.epoch=1
            generated=True;self.generations.append(float(k))
        if self.phase=='pending':
            if state=='unknown':event=True;fallback=True;reason='unknown_before_retirement_fallback'
            elif threat_now:event=True;reason='currently_sustained_threat'
            elif clear_now:
                self.phase='retired_clear';self.last_retired_ms=float(k)
                self.retirements.append(float(k));retired=True
        elif self.phase=='retired_clear':
            # Every sample in the new closed interval must follow retirement.
            # Current minimum history is checked, never an ever-latched event.
            if threat_now and k-20>self.last_retired_ms:
                self.epoch+=1;generated=True;rearmed=True
                self.generations.append(float(k));self.rearms.append(float(k))
                event=True;reason='fresh_sustained_threat_after_retirement'
        if event:
            if self.physical_request_ms is not None:raise ValueError('Repeated physical event')
            self.physical_request_ms=float(k);self.phase='physical_latched';self.fallback=fallback
        return dict(escape_event=event,escape_requested=self.physical_request_ms is not None,
            physical_reason=reason,fallback_event=fallback,pending=self.phase=='pending',
            gate_state=self.phase,candidate_epoch=self.epoch,candidate_generation_event=generated,
            retirement_event=retired,rearm_event=rearmed,
            unknown_after_retirement=bool(self.phase=='retired_clear' and state=='unknown'),
            current_threat_sustained=threat_now,current_clear_sustained=clear_now)
