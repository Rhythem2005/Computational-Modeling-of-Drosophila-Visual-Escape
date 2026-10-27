"""Gate C: measured frozen workloads, bounded estimates and power/storage gates."""
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time
import numpy as np
from connectome.scripts.phase10.common import config
from connectome.scripts.phase10.gru import GRU, Adam
from connectome.scripts.phase10.models import rate_trace
from connectome.scripts.phase10.networks import load_network
from .common import ROOT, OUT, write, arrays, sha, read, sources
from .dataset import Dataset
from .training import batch_inputs, save_state


def power_status():
    result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
    text = result.stdout.strip()
    match = re.search(r'(\d+):(\d+) remaining', text)
    remaining = int(match[1])*3600+int(match[2])*60 if match else None
    return dict(raw=text, exit_code=result.returncode,
                discharging=bool(re.search(r';\s*discharging;', text)), remaining_s=remaining)


def profile():
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    pipeline = FrozenPipeline()
    profile_dir=OUT/'resources/profiles'/str(time.time_ns())
    dataset = Dataset(pipeline, 'uniform_population')
    start = time.perf_counter()
    inputs = dataset.prepare()
    preparation_s = time.perf_counter()-start
    train, val = dataset.records('train'), dataset.records('validation')
    c = config()
    dn = np.array(pipeline.encoder.mapping['channel_index']) < 0
    net = GRU(seed=55100)
    adam = Adam(net.p, .0003, c['adam_beta1'], c['adam_beta2'], c['adam_epsilon'], c['gradient_norm_limit'])
    rng = np.random.default_rng(np.random.SeedSequence([55100, 77]))
    order = rng.permutation(len(train))
    training_batches, validation_batches, checkpoint_s = [], [], []
    start = time.perf_counter()
    for offset in range(0, len(train), c['batch_size']):
        rows = [train[i] for i in order[offset:offset+c['batch_size']]]
        before = time.perf_counter()
        loss, grad = net.loss(batch_inputs(rows, dn), [r['label'] for r in rows], 200, True)
        adam.step(net.p, grad)
        training_batches.append(time.perf_counter()-before)
        # Measure a real full-state checkpoint at every frozen batch boundary.
        state = dict(generation=offset//c['batch_size'], _best={}, rng_state=rng.bit_generator.state,
                     epoch=1, offset=offset+c['batch_size'], order=order.tolist(), history=[], best_bce=None,
                     best_epoch=0, stale=0, contract=dict(profile_only=True, input_identity=inputs))
        checkpoint_start = time.perf_counter()
        save_state(profile_dir/'checkpoint_profile', net, adam, state)
        checkpoint_s.append(time.perf_counter()-checkpoint_start)
        print(f'Profiling full BPTT batch {len(training_batches)}/16', flush=True)
    validation_bce = 0.
    for offset in range(0, len(val), c['batch_size']):
        rows = val[offset:offset+c['batch_size']]
        before = time.perf_counter()
        validation_bce += net.loss(batch_inputs(rows, dn), [r['label'] for r in rows], 200)*len(rows)
        validation_batches.append(time.perf_counter()-before)
    epoch_s = time.perf_counter()-start
    drive = dataset.load(train[0]['scenario_id'])
    weights, setting, _ = load_network('circuit', pipeline.circuit)
    before = time.perf_counter()
    trace = rate_trace(drive, pipeline, weights, setting)
    rate_s = time.perf_counter()-before
    arrays(profile_dir/'rate_profile.npz', score=trace['score'], dn_activity=trace['dn_activity'], final_state=trace['states'][-1])
    arrays(profile_dir/'gru_profile.npz', **net.p)
    rate_bytes = (profile_dir/'rate_profile.npz').stat().st_size
    state_bytes = sum(p.stat().st_size for p in (profile_dir/'checkpoint_profile').glob('*.npz'))
    gru_bytes = (profile_dir/'gru_profile.npz').stat().st_size
    # Uncompressed upper bound avoids assuming all clips compress like one clip.
    score_upper = 744*384*((1000+10000+321)*8+8192) + 72*384*(1000*8+8192)
    checkpoint_upper = 120*(2*4*16241*8 + 200*4096) + 60*16241*8
    inputs_upper = 6*384*(60*321*8+8192)
    # Snapshot, workspace output and transient-copy allowance; 5 GiB reserve.
    required_bytes = 2*(score_upper+checkpoint_upper+inputs_upper) + 5*1024**3
    free = shutil.disk_usage(ROOT).free
    power = power_status()
    hardware = read(OUT/'hardware.json') if (OUT/'hardware.json').exists() else {}
    # This range follows the frozen patience and max epochs, not a smaller budget.
    minimum_training_s = epoch_s*21*120
    maximum_training_s = epoch_s*200*120
    rate_total_s = rate_s*744*384
    from .runtime import check
    live=check(required_bytes)
    blockers=list(live['blockers'])
    if free < required_bytes:
        blockers.append('Available disk is below conservative complete-artifact allowance; budget is not reduced.')
    if hardware.get('physical_memory_bytes', 0) and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > .8*hardware['physical_memory_bytes']:
        blockers.append('Measured peak RSS exceeds 80% of installed physical RAM.')
    report = dict(status='BLOCKED_RESOURCES' if blockers else 'PASS', blockers=blockers,
        profile_only=True, registered_training_trials_completed=0, calibration_conditions_completed=0,
        benchmark_profiling_epochs=1, profiling_training_clips=len(train), profiling_validation_clips=len(val),
        gradient_updates=adam.t, preparation_s=preparation_s, measured_epoch_s=epoch_s,
        training_batch_s=training_batches, validation_batch_s=validation_batches, checkpoint_write_s=checkpoint_s,
        validation_bce=validation_bce/len(val), validation_evidence='Profiling/calibration only; no model selected or frozen.',
        rate_clip_s=rate_s, maximum_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        rss_units='bytes on macOS', representative_compressed_rate_output_bytes=rate_bytes,
        representative_gru_parameter_bytes=gru_bytes, retained_profile_checkpoint_bytes=state_bytes,
        estimated_full_training_range_s=[minimum_training_s, maximum_training_s], estimated_rate_inference_s=rate_total_s,
        estimate_limits='Single uniform-mapping epoch/one circuit clip; ignores spatial input preparation and candidate decoding; throughput may vary with mapping, cache, thermal state and power. Estimates are not completed work.',
        conservative_disk_allowance_bytes=required_bytes, disk_free_bytes=free, power=power,
        hardware=hardware, threads={k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},
        held_out_inference_runs=0, input_identity=inputs,live_preflight=live,
        phase11_sources_sha256=sources(),profile_directory=str(profile_dir.relative_to(ROOT)))
    write(OUT/'gate_C.json', report)
    print('Gate C:', report['status'], f'epoch {epoch_s:.3f}s, peak RSS {report["maximum_resident_bytes"]/1024**2:.1f} MiB', flush=True)
    return report
