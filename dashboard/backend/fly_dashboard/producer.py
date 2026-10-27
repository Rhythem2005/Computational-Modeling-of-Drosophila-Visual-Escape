"""Opt-in client for an independently authorized producer; no experiment code."""
import json
import time
from urllib.request import Request,urlopen
from urllib.error import HTTPError

class DashboardPublisher:
    def __init__(self,base_url,token):
        self.base=base_url.rstrip('/');self.token=token;self.session_id=None
    def _request(self,path,value=None,method='POST'):
        data=None if value is None else json.dumps(value,allow_nan=False).encode()
        request=Request(self.base+path,data=data,headers={'Content-Type':'application/json','X-Fly-Ingest-Token':self.token},method=method)
        with urlopen(request,timeout=2) as response:return json.load(response)
    def _post(self,path,value):return self._request(path,value)
    def open(self,*,name,protocol,controller,source_note,world_config):
        deadline=time.monotonic()+20
        while True:
            sessions=self._request('/api/v1/live',method='GET')['sessions']
            if len(sessions)<4:break
            ended=[old for old in sessions if not old['active'] and old['protocol']==protocol]
            if not ended:raise RuntimeError('Live capacity is occupied by active/unrelated sessions')
            removed=False
            for old in ended:
                try:self._request('/api/v1/live/'+old['id'],method='DELETE');removed=True;break
                except HTTPError as e:
                    if e.code!=409:raise
            if removed:continue
            if time.monotonic()>=deadline:raise RuntimeError('Ended viewers did not detach within startup cleanup budget')
            time.sleep(.25)
        value=self._post('/api/v1/live',dict(name=name,protocol=protocol,controller=controller,source_note=source_note,world_config=world_config))
        self.session_id=value['id'];return self.session_id
    def publish(self,frame):
        if self.session_id is None:raise ValueError('Open a session first')
        return self._post(f'/api/v1/live/{self.session_id}/frames',frame)
    def close(self):
        if self.session_id is not None:self._post(f'/api/v1/live/{self.session_id}/end',{})
