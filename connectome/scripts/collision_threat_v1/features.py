"""Causal pixel measurements. No world, scenario, label, model, or onset inputs."""
from dataclasses import dataclass
from numbers import Real
import math
import numpy as np
from scipy.ndimage import label


@dataclass(frozen=True)
class Camera:
    width: int
    height: int
    center_x: float
    center_y: float
    focal_px: float
    fps: float
    background: int
    min_contrast: int

    def __post_init__(self):
        if (type(self.width) is not int or type(self.height) is not int
                or self.width<2 or self.height<2
                or not all(isinstance(x,Real) and not isinstance(x,bool) and math.isfinite(x)
                           for x in (self.center_x,self.center_y,self.focal_px,self.fps))
                or not 0<=self.center_x<self.width or not 0<=self.center_y<self.height
                or self.focal_px<=0 or self.fps<=0
                or type(self.background) is not int or not 0<=self.background<=255
                or type(self.min_contrast) is not int or not 1<=self.min_contrast<=255):
            raise ValueError('Invalid camera/segmentation contract')


def camera_from_config(world_config, encoder_config):
    """Copy only approved image constants, not the rest of the world config."""
    return Camera(width=world_config['camera_width'],height=world_config['camera_height'],
                  center_x=world_config['camera_center_px'][0],center_y=world_config['camera_center_px'][1],
                  focal_px=world_config['camera_focal_px'],fps=world_config['camera_fps'],
                  background=world_config['background_uint8'],min_contrast=encoder_config['min_contrast_uint8'])


class FeatureExtractor:
    """One observation in, one measurement record out; adjacent-frame derivatives."""
    def __init__(self,camera):
        if not isinstance(camera,Camera):
            raise ValueError('Explicit Camera required')
        self.camera=camera
        self.reset()

    def reset(self):
        self.previous=None

    def update(self,frame,timestamp_s):
        c=self.camera
        if (not isinstance(frame,np.ndarray) or frame.dtype!=np.uint8
                or frame.shape!=(c.height,c.width)):
            raise ValueError('Expected one uint8 camera frame with the declared dimensions')
        if (isinstance(timestamp_s,bool) or not isinstance(timestamp_s,Real)
                or not math.isfinite(timestamp_s) or timestamp_s<0):
            raise ValueError('Expected a finite nonnegative timestamp in seconds')
        timestamp_s=float(timestamp_s)
        previous=self.previous
        if previous is not None and timestamp_s<=previous['timestamp_s']:
            raise ValueError('Timestamps must be strictly increasing; reset between episodes')
        mask=np.abs(frame.astype(np.int16)-c.background)>=c.min_contrast
        area=int(mask.sum())
        _,components=label(mask,structure=np.ones((3,3),dtype=np.uint8))
        border=bool(mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any())
        dominant=area>=frame.size/2
        reasons=[]
        if not area:reasons.append('no_visible_foreground_depth_unknown')
        if dominant:reasons.append('foreground_not_minority')
        if components>1:reasons.append('multiple_foreground_components')
        if border:reasons.append('foreground_touches_border')
        valid=not reasons
        row=dict(timestamp_s=timestamp_s,area_px=area,component_count=int(components),
                 border_contact=border,foreground_dominant=dominant,measurement_valid=valid,
                 radius_px=None,centroid_x_px=None,centroid_y_px=None,normalized_x=None,normalized_y=None,
                 bearing_rad=None,half_extent_rad=None,radius_rate_px_s=None,
                 centroid_x_rate_px_s=None,centroid_y_rate_px_s=None,
                 bearing_rate_rad_s=None,extent_rate_rad_s=None,
                 interval_s=None,timestamp_gap=False,motion_valid=False,reasons=reasons)
        if valid:
            yy,xx=np.nonzero(mask)
            radius=float(np.sqrt(area/np.pi));cx=float(xx.mean());cy=float(yy.mean())
            row.update(radius_px=radius,centroid_x_px=cx,centroid_y_px=cy,
                       normalized_x=(cx-c.center_x)/c.focal_px,normalized_y=(cy-c.center_y)/c.focal_px,
                       bearing_rad=float(np.arctan((cx-c.center_x)/c.focal_px)),
                       half_extent_rad=float(np.arctan(radius/c.focal_px)))
        if previous is None:
            row['reasons'].append('insufficient_history')
        else:
            dt=timestamp_s-previous['timestamp_s'];row['interval_s']=dt
            # Machine-roundoff allowance for n/fps subtraction, not a fitted
            # sensory or threat threshold. Missing observations break history.
            roundoff=64*np.finfo(np.float64).eps*max(1.,abs(timestamp_s))
            gap=abs(dt-1/c.fps)>roundoff;row['timestamp_gap']=bool(gap)
            if gap:row['reasons'].append('timestamp_gap')
            if not previous['measurement_valid']:row['reasons'].append('previous_measurement_invalid')
            if valid and previous['measurement_valid'] and not gap:
                for value,rate in [('radius_px','radius_rate_px_s'),('centroid_x_px','centroid_x_rate_px_s'),
                                   ('centroid_y_px','centroid_y_rate_px_s'),('bearing_rad','bearing_rate_rad_s'),
                                   ('half_extent_rad','extent_rate_rad_s')]:
                    row[rate]=(row[value]-previous[value])/dt
                row['motion_valid']=True
        for key,value in row.items():
            if isinstance(value,float) and not math.isfinite(value):
                raise FloatingPointError(f'Nonfinite measurement: {key}')
        # Store private scalar history, never a mutable caller frame or record.
        self.previous={k:row[k] for k in ('timestamp_s','measurement_valid','radius_px',
                       'centroid_x_px','centroid_y_px','bearing_rad','half_extent_rad')}
        return row


def extract(frames,timestamps_s,camera):
    if (not isinstance(frames,np.ndarray) or frames.dtype!=np.uint8 or frames.ndim!=3
            or not isinstance(timestamps_s,np.ndarray) or timestamps_s.dtype!=np.float64
            or timestamps_s.shape!=(len(frames),) or len(frames)==0):
        raise ValueError('Expected nonempty uint8 frames and matching float64 seconds')
    extractor=FeatureExtractor(camera)
    return [extractor.update(frame,t) for frame,t in zip(frames,timestamps_s)]


def available_tick(timestamp_s):
    """First k satisfying timestamp <= k/1000 under the exact scheduler comparison."""
    k=math.floor(timestamp_s*1000)
    while k/1000<timestamp_s:k+=1
    while k>0 and (k-1)/1000>=timestamp_s:k-=1
    return k
