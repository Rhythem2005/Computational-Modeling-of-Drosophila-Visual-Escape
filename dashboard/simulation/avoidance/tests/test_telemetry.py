from threading import Event
from dashboard.simulation.avoidance.telemetry import AsyncObserver

def test_slow_display_drops_samples_but_retains_events():
    blocked=Event();started=Event();received=[]
    def send(p):
        started.set();blocked.wait(1);received.append(p)
    observer=AsyncObserver(send,capacity=1)
    observer.publish(dict(time_ms=0,events=[]));assert started.wait(1)
    observer.publish(dict(time_ms=1,events=[dict(kind='request',time_ms=1)]))
    observer.publish(dict(time_ms=2,events=[dict(kind='motion',time_ms=2)]))
    assert observer.dropped==1
    blocked.set();report=observer.close()
    assert not report['transport_error']
    assert [e['kind'] for e in received[-1]['events']]==['request','motion']
