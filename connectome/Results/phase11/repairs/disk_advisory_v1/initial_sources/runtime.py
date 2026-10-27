"""Continuous-execution resource checks; no sessions, cooling or trial limits."""
from contextlib import contextmanager
import ctypes
import fcntl
import json
import os
import re
import shutil
import subprocess
import time
from .common import ROOT, OUT, write, raw_sources, BASE, sha

MINIMUM_BATTERY_PERCENT = 20


@contextmanager
def lease():
    path = OUT/'manual_worker.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another continuous Phase 11 launcher is active') from error
        try:
            f.seek(0); f.truncate(); json.dump(dict(pid=os.getpid()), f); f.flush()
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def thermal():
    try:
        ctypes.CDLL('/System/Library/Frameworks/Foundation.framework/Foundation')
        objc = ctypes.CDLL('/usr/lib/libobjc.A.dylib')
        objc.objc_getClass.argtypes=[ctypes.c_char_p]; objc.objc_getClass.restype=ctypes.c_void_p
        objc.sel_registerName.argtypes=[ctypes.c_char_p]; objc.sel_registerName.restype=ctypes.c_void_p
        ptr=ctypes.CFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p)(('objc_msgSend',objc))
        integer=ctypes.CFUNCTYPE(ctypes.c_longlong,ctypes.c_void_p,ctypes.c_void_p)(('objc_msgSend',objc))
        info=ptr(objc.objc_getClass(b'NSProcessInfo'),objc.sel_registerName(b'processInfo'))
        value=int(integer(info,objc.sel_registerName(b'thermalState')))
        if value not in (0,1,2,3): raise ValueError('Unknown OS pressure')
        return dict(available=True,state=value,name=['nominal','fair','serious','critical'][value],temperature_c=None)
    except Exception as error:
        return dict(available=False,state=None,error=str(error),temperature_c=None)


def command(args):
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=5)
        return result.returncode,result.stdout,result.stderr
    except (OSError,subprocess.TimeoutExpired) as error:
        return -1,'',str(error)


def sample():
    code,power,power_error=command(['pmset','-g','batt'])
    match=re.search(r'(\d+)%;\s*([^;]+)',power)
    ps_code,processes,ps_error=command(['/bin/ps','-axo','pid=,ppid=,command='])
    rows=[]
    for line in processes.splitlines():
        parts=line.strip().split(None,2)
        if len(parts)==3 and parts[0].isdigit() and parts[1].isdigit(): rows.append((int(parts[0]),int(parts[1]),parts[2]))
    allowed={os.getpid(),int(os.environ.get('FLY_PHASE11_LAUNCHER_PID',os.getpid()))}
    for _ in rows:
        expanded=allowed|{pid for pid,ppid,_ in rows if ppid in allowed}
        if expanded==allowed: break
        allowed=expanded
    workers=[dict(pid=pid,command=cmd) for pid,_,cmd in rows if pid not in allowed
             and 'python' in cmd.split()[0].lower() and re.search(r'-m\s+connectome\.scripts\.phase11\.(launch|runner)\b',cmd)]
    vm_code,vm,vm_error=command(['/usr/bin/vm_stat'])
    page=re.search(r'page size of (\d+) bytes',vm)
    memory=None
    if vm_code==0 and page:
        counts=[re.search(r'Pages '+name+r':\s*(\d+)',vm) for name in ('free','inactive','speculative')]
        if all(counts): memory=sum(int(m[1]) for m in counts)*int(page[1])
    return dict(timestamp=time.time(),disk_free_bytes=shutil.disk_usage(ROOT).free,
        ac_connected="Now drawing from 'AC Power'" in power,power_status=match[2].strip().lower() if match else 'unknown',
        battery_percent=int(match[1]) if match else None,power_query_ok=code==0,power_raw=power.strip(),power_error=power_error,
        process_query_ok=ps_code==0,other_workers=workers,process_error=ps_error,
        available_memory_estimate_bytes=memory,memory_estimate='vm_stat free + inactive + speculative pages; reclaimable estimate',
        memory_error=vm_error,thermal=thermal())


def assess(first,second,minimum_disk):
    errors=[]
    if second['disk_free_bytes']<minimum_disk: errors.append('INSUFFICIENT_DISK')
    stable=(first['battery_percent'] is not None and second['battery_percent'] is not None
            and second['battery_percent']>=first['battery_percent'])
    status=second['power_status']
    if not first['power_query_ok'] or not second['power_query_ok']:
        errors.append('POWER_STATUS_NOT_VERIFIED')
    elif not second['ac_connected']:
        levels=(first['battery_percent'],second['battery_percent'])
        if any(type(level) is not int or not 0 <= level <= 100 for level in levels):
            errors.append('BATTERY_LEVEL_NOT_VERIFIED')
        elif min(levels)<MINIMUM_BATTERY_PERCENT:
            errors.append('BATTERY_BELOW_20_PERCENT')
        if status not in ('discharging','charged','not charging'):
            errors.append('BATTERY_POWER_STATUS_NOT_VERIFIED')
    else:
        if first['battery_percent'] is not None and second['battery_percent'] is not None and second['battery_percent']<first['battery_percent']:
            errors.append('BATTERY_PERCENT_DECREASED')
        if status=='discharging': errors.append('BATTERY_DISCHARGING')
        elif status not in ('charging','charged','finishing charge') and not(status=='not charging' and stable): errors.append('CHARGING_OR_STABLE_NOT_VERIFIED')
    if not second['process_query_ok']: errors.append('WORKER_QUERY_UNAVAILABLE')
    elif second['other_workers']: errors.append('ANOTHER_PHASE11_WORKER')
    available=second['available_memory_estimate_bytes']
    if available is None or available<2*1024**3: errors.append('AVAILABLE_MEMORY_BELOW_2_GIB_OR_UNKNOWN')
    if second['thermal']['available'] and second['thermal']['state']>=2: errors.append('SERIOUS_OR_CRITICAL_THERMAL_PRESSURE')
    return errors


def check(minimum_disk):
    first=sample(); time.sleep(2); second=sample()
    errors=assess(first,second,minimum_disk)
    result=dict(status='PASS' if not errors else 'BLOCKED_RESOURCES',blockers=errors,samples=[first,second])
    certificate=BASE/'repairs/battery_power_v1/source_compatibility.json'
    result.update(power_policy=dict(ac_required=False,minimum_battery_percent=MINIMUM_BATTERY_PERCENT,
                  startup_check_only=True), execution_sources_sha256=raw_sources(),
                  power_policy_certificate_sha256=sha(certificate) if certificate.exists() else None)
    write(OUT/'runtime_preflight.json',result)
    return result
