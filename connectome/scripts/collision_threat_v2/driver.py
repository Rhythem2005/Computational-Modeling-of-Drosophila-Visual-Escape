"""Eight fixed ablations, without changing any v1 controller or decoder."""
from connectome.scripts.collision_threat_v1.hybrid import Driver as V1Driver
from .rule import FiniteThreatRule,KnownSizePrior
from .gate import RetirementGate

ROLES={
 'no_action':('no_action',False,False),
 'circuit':('circuit',False,False),
 'point_standalone_v1':('closest_approach_rule',False,False),
 'finite_standalone_v2':('closest_approach_rule',True,False),
 'point_original_gate_v1':('circuit_threat_gate',False,False),
 'point_retirement_gate_v2':('circuit_threat_gate',False,True),
 'finite_original_gate_v2':('circuit_threat_gate',True,False),
 'finite_retirement_gate_v2':('circuit_threat_gate',True,True)}

class Driver(V1Driver):
    def __init__(self,model,pipeline,camera,legacy_rows,prior):
        if model not in ROLES:raise ValueError('Unregistered v2 comparison condition')
        alias,finite,retirement=ROLES[model]
        super().__init__(alias,pipeline,camera,legacy_rows)
        self.model=model;self.finite=finite;self.retirement=retirement
        self.prior=prior if finite else None
        if finite:self.rule=FiniteThreatRule(camera,prior)
        if retirement:self.gate=RetirementGate()

    def sample(self,k,drive):
        if not self.retirement:
            out=super().sample(k,drive)
            phase=('physical_latched' if out['escape_requested'] else 'pending' if out['pending'] else 'unarmed') if self.gate else 'not_applicable'
            out.update(gate_state=phase,candidate_epoch=int(bool(self.gate and self.gate.pending)),
                candidate_generation_event=bool(self.gate and out['legacy_escape_event']),
                retirement_event=False,rearm_event=False,unknown_after_retirement=False,
                current_threat_sustained=bool(self.rule and out['eligible'] and out['sustained_score']>=1),
                current_clear_sustained=False)
            return out
        score=self.legacy.score(drive)
        legacy=self.legacy_stream.update(float(k),score)
        rule=self.rule.sample(k)
        if rule['state']=='unknown':self.unknown_ticks+=1
        physical=self.gate.update(k,legacy['escape_requested'],rule['state'])
        assert physical['current_threat_sustained']==rule['currently_sustained_threat']
        self.fallback_count+=int(physical['fallback_event'])
        if physical['escape_event']:
            if self.physical_request_ms is not None:raise ValueError('Repeated physical request')
            self.physical_request_ms=float(k)
        return dict(score=rule['score'],sustained_score=rule['sustained_score'],eligible=rule['eligible'],
            **physical,legacy_score=score,legacy_sustained_score=legacy['sustained_score'],
            legacy_escape_event=legacy['escape_event'],legacy_escape_requested=legacy['escape_requested'],
            rule_state=rule['state'],rule_reason=rule['reason'])
