"""Bounded nonblocking observer. Full-resolution evidence is saved separately."""
from queue import Queue,Full
from threading import Thread
import time

class AsyncObserver:
    def __init__(self,send,capacity=2):
        self.send=send;self.queue=Queue(maxsize=capacity);self.dropped=0;self.error=None
        self.last_error=None;self.pending_events=[];self.thread=Thread(target=self._run,daemon=True);self.thread.start()
    def _run(self):
        while True:
            value=self.queue.get()
            try:
                if value is None:return
                try:self.send(value)
                except Exception as e:self.error=str(e)
            finally:self.queue.task_done()
    def publish(self,packet):
        # Event IDs survive discarded visualization samples; science arrays never use this queue.
        self.pending_events.extend(packet.get('events',[]));packet=dict(packet,events=list(self.pending_events))
        try:self.queue.put_nowait(packet);self.pending_events=[]
        except Full:
            try:old=self.queue.get_nowait();self.queue.task_done();self.pending_events=old.get('events',[])+self.pending_events
            except Exception:pass
            packet=dict(packet,events=list(self.pending_events));self.queue.put_nowait(packet);self.pending_events=[];self.dropped+=1
    def close(self,timeout=5):
        # Only completion may wait; no scientific tick waits for transport.
        deadline=time.monotonic()+timeout
        while self.queue.unfinished_tasks and time.monotonic()<deadline:time.sleep(.01)
        try:self.queue.put_nowait(None)
        except Full:self.error=self.error or 'Telemetry did not drain before shutdown'
        self.thread.join(max(0,deadline-time.monotonic()))
        return dict(dropped_display_frames=self.dropped,transport_error=self.error,pending_events=len(self.pending_events))
