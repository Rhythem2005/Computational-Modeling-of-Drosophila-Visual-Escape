"""Isolated feasibility measurements. Never launches a registered training trial."""
import argparse
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time


def read(path):
    return json.loads(Path(path).read_text())


def write(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metal_probe():
    metal = ctypes.CDLL('/System/Library/Frameworks/Metal.framework/Metal')
    objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
    metal.MTLCreateSystemDefaultDevice.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    ptr = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    uint = ctypes.CFUNCTYPE(ctypes.c_ulonglong, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    string = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    dev = metal.MTLCreateSystemDefaultDevice()
    result = dict(metal_device_available=bool(dev), probe='Native Metal MTLCreateSystemDefaultDevice; no GPU workload')
    if dev:
        name = ptr(dev, objc.sel_registerName(b'name'))
        result['device_name'] = string(name, objc.sel_registerName(b'UTF8String')).decode()
        for key in ('hasUnifiedMemory', 'isLowPower', 'recommendedMaxWorkingSetSize', 'currentAllocatedSize'):
            result[key] = uint(dev, objc.sel_registerName(key.encode()))
    return result


def summary(values):
    return dict(repetitions=len(values), median_s=statistics.median(values), min_s=min(values), max_s=max(values), samples_s=values)


def worker(root, output, label):
    sys.path.insert(0, str(root))
    import numpy as np
    from connectome.scripts.phase10.gru import GRU, Adam, _validate_sets
    from connectome.scripts.phase10.common import config
    from connectome.scripts.phase10.data import TrainingDataset, validate_coverage
    from connectome.scripts.phase7.pipeline import FrozenPipeline
    from connectome.scripts.phase11.dataset import Dataset
    from connectome.scripts.phase11.training import batch_inputs, save_state
    from connectome.scripts.phase11.common import OUT
    start = time.perf_counter()
    c = config()
    pipeline = FrozenPipeline()
    dataset = Dataset(pipeline, 'uniform_population')
    input_identity = dataset.prepare()
    train, val = dataset.records('train'), dataset.records('validation')
    _validate_sets(train, val)
    dn = np.array(pipeline.encoder.mapping['channel_index']) < 0
    # The seed/order/scaling match the first predeclared trial; reset every epoch
    # repetition, discard weights, never select a checkpoint/rate/threshold.
    rng = np.random.default_rng(np.random.SeedSequence([55100, 77]))
    order = rng.permutation(len(train)).tolist()
    batches = [[train[i] for i in order[k:k+16]] for k in range(0, 256, 16)]
    x = batch_inputs(batches[0], dn)
    y = [r['label'] for r in batches[0]]
    net = GRU(seed=55100)
    assert net.parameter_count == 16241 and x.shape == (16, 1000, 321) and x.dtype == np.float64
    setup_s = time.perf_counter()-start
    times = {}
    warmups = {}

    def timed(name, function, repeats):
        t = time.perf_counter(); result = function(); warmups[name] = time.perf_counter()-t
        samples = []
        for _ in range(repeats):
            t = time.perf_counter(); result = function(); samples.append(time.perf_counter()-t)
        times[name] = summary(samples)
        return result

    logits = timed('forward_batch16', lambda: net.forward(x), 7)
    loss, gradients = timed('full_bptt_batch16', lambda: net.loss(x, y, 200, True), 7)
    def optimizer_only():
        model = GRU(seed=55100)
        opt = Adam(model.p, .0003, .9, .999, 1e-8, 5.)
        # Parameter initialization deliberately excluded from optimizer timing.
        t = time.perf_counter(); opt.step(model.p, gradients)
        return time.perf_counter()-t
    warmups['adam_update'] = optimizer_only()
    times['adam_update'] = summary([optimizer_only() for _ in range(15)])
    def batch_update():
        model = GRU(seed=55100)
        opt = Adam(model.p, .0003, .9, .999, 1e-8, 5.)
        t = time.perf_counter()
        value, grad = model.loss(x, y, 200, True)
        opt.step(model.p, grad)
        return time.perf_counter()-t
    warmups['bptt_and_adam_batch16'] = batch_update()
    times['bptt_and_adam_batch16'] = summary([batch_update() for _ in range(7)])

    def validation_only():
        total = 0.
        for offset in range(0, 128, 16):
            rows = val[offset:offset+16]
            total += net.loss(batch_inputs(rows, dn), [r['label'] for r in rows], 200)*len(rows)
        return total/128
    timed('validation128_including_input_loading', validation_only, 5)

    # Equivalent one-epoch workloads, including actual frame-cache loading and
    # optional exact production checkpoint payloads/writes in the disposable copy.
    def epoch(with_checkpoint, iteration):
        model = GRU(seed=55100)
        opt = Adam(model.p, .0003, .9, .999, 1e-8, 5.)
        state = dict(generation=0, epoch=1, offset=0, order=order, rng_state=rng.bit_generator.state,
           history=[], best_bce=None, best_epoch=0, stale=0, train_sum=0., clipped=0,
           contract=dict(profile_only=True, input_identity=input_identity), _best={}, finished=False)
        directory = OUT/'acceleration_benchmark_temp'/label/f'epoch_{iteration}'
        started = time.perf_counter()
        for rows in batches:
            value, grad = model.loss(batch_inputs(rows, dn), [r['label'] for r in rows], 200, True)
            update = opt.step(model.p, grad)
            state['train_sum'] += value*len(rows)
            state['clipped'] += int(update['applied_scale'] < 1)
            state['offset'] += len(rows)
            if with_checkpoint:
                save_state(directory, model, opt, state)
        train_s = time.perf_counter()-started
        before = time.perf_counter(); validation_loss = 0.
        for offset in range(0, 128, 16):
            rows = val[offset:offset+16]
            validation_loss += model.loss(batch_inputs(rows, dn), [r['label'] for r in rows], 200)*len(rows)
        validation_loss /= 128
        val_s = time.perf_counter()-before
        if with_checkpoint:
            state.update(epoch=2, offset=0, order=None, history=[dict(epoch=1, training_bce=state['train_sum']/256,
                         validation_bce=validation_loss, gradient_clipped_batches=state['clipped'])],
                         best_bce=validation_loss, best_epoch=1, _best={k:v.copy() for k,v in model.p.items()})
            save_state(directory, model, opt, state)
        elapsed = time.perf_counter()-started
        return dict(total_s=elapsed, training_s=train_s, validation_s=val_s,
                    validation_bce=validation_loss, updates=opt.t), model
    epoch_results = {}
    final_net = None
    for checkpoint in (False, True):
        name = 'epoch_with_checkpoints' if checkpoint else 'epoch_without_checkpoints'
        warm, _ = epoch(checkpoint, name+'_warmup')
        warmups[name] = warm['total_s']
        details = []
        for k in range(5):
            detail, final_net = epoch(checkpoint, name+str(k)); details.append(detail)
        times[name] = summary([r['total_s'] for r in details])
        epoch_results[name] = details
    # Independent finite difference check on real inputs for 11 selected entries;
    # plus frozen-code repeatability across identical controlled updates.
    checks = []
    for key in net.p:
        index = tuple(int(i) for i in np.unravel_index(np.argmax(np.abs(gradients[key])), gradients[key].shape))
        old = net.p[key][index]; epsilon = 1e-5
        net.p[key][index] = old+epsilon; upper = net.loss(x, y, 200)
        net.p[key][index] = old-epsilon; lower = net.loss(x, y, 200)
        net.p[key][index] = old
        numeric = (upper-lower)/(2*epsilon); analytic = float(gradients[key][index])
        tolerance = 2e-8+2e-5*abs(numeric)
        checks.append(dict(parameter=key, numerical=float(numeric), analytical=analytic,
                           absolute_error=abs(numeric-analytic), tolerance=tolerance, passed=abs(numeric-analytic)<=tolerance))
    a, b = GRU(seed=55100), GRU(seed=55100)
    oa, ob = Adam(a.p, .0003), Adam(b.p, .0003)
    for _ in range(3):
        for model, opt in ((a, oa), (b, ob)):
            _, grad = model.loss(x, y, 200, True); opt.step(model.p, grad)
    assert all(np.array_equal(a.p[k],b.p[k]) for k in a.p)
    assert all(check['passed'] for check in checks)
    # Array payload permits cross-process/thread-hint output and gradient checks.
    comparison_file = output.with_suffix('.npz')
    np.savez_compressed(comparison_file, logits=logits, **{'g_'+k:v for k,v in gradients.items()},
                        **{'updated_'+k:v for k,v in a.p.items()}, **{'epoch_'+k:v for k,v in final_net.p.items()})
    cfg = io.StringIO()
    from contextlib import redirect_stdout
    with redirect_stdout(cfg): np.show_config()
    result = dict(label=label, status='PASS_CPU_BENCHMARK_ONLY', python=sys.version, numpy=np.__version__,
       environment={k:os.environ.get(k) for k in ('VECLIB_MAXIMUM_THREADS','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},
       numpy_build=cfg.getvalue(), setup_s=setup_s, warmup_s=warmups,
       timing=times, epoch_details=epoch_results, comparison_arrays_sha256=sha(comparison_file),
       finite_difference_checks=checks, controlled_three_update_repeatable=True,
       maximum_resident_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
       workload=dict(parameters=16241, batch_size=16, steps=1000, inputs=321, hidden=16, dtype='float64',
                     seed=55100, rate=.0003, input_identity=input_identity),
       registered_training_trials=0, calibrations=0, held_out_inference_runs=0,
       synchronization='Synchronous CPU calls; GPU synchronization/compilation not measured.')
    write(output, result)
    print(label, 'median full epoch',times['epoch_with_checkpoints']['median_s'],
          'peak MiB',result['maximum_resident_bytes']/1024**2, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe-metal', action='store_true')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--label', default='cpu_single_thread_hint')
    args = parser.parse_args()
    if args.probe_metal:
        result = metal_probe()
        if args.output: write(args.output, result)
        print(json.dumps(result))
    else:
        worker(args.root, args.output, args.label)
