"""Behavioral diagnostics are separate from the unchanged episode BCE objective."""
import numpy as np
from connectome.scripts.phase10.calibration import calibrate
from connectome.scripts.phase8.decoder import decode_score, Threshold


def behavior(records, threshold):
    times = np.arange(1000, dtype=np.float64)
    events = []
    for row in records:
        first = decode_score(times, row['score'], 1000., Threshold(**threshold)).first_event_ms
        events.append(dict(scenario_id=row['scenario_id'], label=row['label'], role=row['role'],
             first_event_ms=first, early=first is not None and first < 200,
             timely=first is not None and 200 <= first < 1000,
             missed=row['label'] == 1 and first is None,
             late_within_observed_window=False))
    pos = [r for r in events if r['label'] == 1]
    neg = [r for r in events if r['label'] == 0]
    latency = [r['first_event_ms']-200 for r in pos if r['timely']]
    return dict(evidence_type='training_or_validation_calibration_not_generalization',
       timely_tpr=sum(r['timely'] for r in pos)/len(pos), full_episode_negative_fpr=sum(r['first_event_ms'] is not None for r in neg)/len(neg),
       early_alarms=sum(r['early'] for r in events), early_positive_alarms=sum(r['early'] for r in pos),
       missed_positives=sum(r['missed'] for r in pos), non_timely_positives=sum(not r['timely'] for r in pos),
       median_detected_latency_ms=float(np.median(latency)) if latency else None,
       all_positive_latency_ms=float(np.mean([r['first_event_ms']-200 if r['timely'] else 800 for r in pos])),
       late_detection_note='Events at/after 1000 ms are excluded; no post-horizon inference. Absence of timely detection is retained as a miss or early alarm.',
       per_episode=events)


def assess(training, validation, identity, *, smoke=False):
    result = calibrate(training, validation, identity, smoke=smoke)
    eligible = [r for r in result['assessments'] if r['full_episode_fpr'] <= .05]
    finite = [r for r in eligible if r['threshold']['kind'] == 'finite']
    result['feasibility'] = dict(eligible_candidates=len(eligible), eligible_finite_candidates=len(finite),
         no_eligible_threshold=not eligible, no_eligible_finite_threshold=not finite,
         selected_silent_sentinel=result['threshold']['kind'] == 'always_silent', fpr_constraint=.05,
         rule_relaxed=False, note='The declared always-silent sentinel guarantees feasibility for valid finite scores.')
    result['behavior'] = {split: behavior(rows, result['threshold']) for split, rows in (('train', training), ('validation', validation))}
    result['validation_reuse'] = 'Checkpoint, learning-rate and threshold selection share validation under frozen protocol; calibration evidence only.'
    return result
