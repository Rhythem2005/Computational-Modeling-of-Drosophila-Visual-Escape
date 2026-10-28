export type Vec2 = [number,number];
export type Position = Vec2 | [number,number,number];
export type Quaternion=[number,number,number,number];
export interface SolidPart {shape:'sphere'|'box';offset:[number,number,number];quaternion:Quaternion;color:[number,number,number];radius?:number|null;half_extents?:[number,number,number]|null}
export interface RoomSolid {id:string;parts:SolidPart[];keyframes:{time_ms:number;position:[number,number,number]}[]}
export interface RigView {id:string;quaternion:Quaternion;width:number;height:number;focal_px:number}
export interface Episode {id:string;name:string;family:string;experiment:string;scenario:string;model:string;repeat:number;duration_ms:number;danger:boolean|null;escape_success:boolean|null;false_alarm:boolean|null;request_ms:number|null;failure:{kind:string;time_ms:number}|null;source:string;expected_sha256:string;mode:string;mapping?:string;mapping_seed?:number|null}
export interface Catalog {episodes:Episode[];diagnostics:{source:string;error:string}[];source_count:number;policy:string}
export interface Node {id:number;type:string;side:string;population:string;role:string}
export interface Edge {source:number;target:number;weight:number;normalized:number;category:string}
export interface Graph {nodes:Node[];edges:Edge[];circuit_id:string;dataset:string;coordinate_semantics:string;sha256:{nodes:string;edges:string}}
export interface WorldConfig {fly_radius:number;room_flight?:boolean;neural_role?:string;camera_rig?:RigView[];room_scene?:{static_solids:RoomSolid[];dynamic_solids:RoomSolid[]};world_dimension?:2|3;bounds?:Vec2[];bounds_xy?:[Vec2,Vec2];duration_ms?:number;camera_width?:number;camera_height?:number;camera_focal_px?:number;actuation_delay_ms?:number;escape_speed_max?:number;world_units?:string;[key:string]:unknown}
export interface Metrics {danger:boolean|null;escape_success:boolean|null;false_alarm:boolean|null;first_request_ms:number|null;internal_request_ms?:number|null;scheduled_actuation_ms?:number|null;first_motion_ms?:number|null;minimum_swept_clearance?:number;final_clearance?:number;path_length?:number;failure?:{kind:string;time_ms:number}|null;[key:string]:unknown}
export interface ReplayEvent {time_ms:number;kind:string;label:string}
export interface Replay {
 episode:Episode;config:WorldConfig;scenario:{scenario_id:string;fly_position:Position;obstacles:{id:string;position:Position;velocity?:Position;radius:number;parts?:SolidPart[]|null}[]};metrics:Metrics;
 threshold:{kind:string;value:number|null}|null;assumptions?:string|null;integrity:{status:string;sha256:string;schema:string};
 world:{times_ms:number[];fly:Position[];quaternion_xyzw?:Quaternion[];obstacles:Position[][];speed:(number|null)[]};
 neural:{kind:'anatomical'|'gru_hidden'|'unavailable';times_ms:number[];values:number[][];ids:(number|string)[]};
 decision:{times_ms:number[];traces:Record<string,(number|string|boolean|null)[]>};
 encoder:{times_ms:number[];channels:number[][];drive:number[][];valid:(boolean|null)[];decision_frame_indices:number[];ids:number[]};
 measurements:{times_ms:number[];values:Record<string,unknown[]>};
 camera:{times_ms:number[];width:number;height:number;columns:number;count:number;atlas_url:string;view_ids?:string[];mosaic_columns?:number};
 events:ReplayEvent[];duration_ms:number;source_mode:string;live_image?:string|null;
}
export interface ProjectStatus {training:{completed:number;planned:number;calibrated:number;calibration_planned:number;process_state:string}|null;execution_policy:string;world:string;limitations:string[]}
export interface LiveSpec {id:string;name:string;protocol:string;controller:string;source_note:string;world_config:WorldConfig;active:boolean;frame_count?:number;last_time_ms?:number|null}
export interface LiveFrame {time_ms:number;fly_quaternion_xyzw?:Quaternion|null;sensor_views?:{id:string;time_ms:number;quaternion_xyzw:Quaternion;png_base64:string}[];decision_timestamp_ms?:number|null;neural_timestamp_ms?:number|null;fly:Position;obstacles:{id:string;position:Position;radius:number;parts?:SolidPart[]|null}[];speed:number|null;score:number|null;sustained_score:number|null;gate_state:string|null;rule_state:string|null;encoder_channels:number[]|null;encoder_drive:number[]|null;encoder_body_ids:number[];encoder_valid:boolean|null;neural_kind:Replay['neural']['kind'];neural_ids:(number|string)[];neural_values:number[];camera_timestamp_ms:number|null;camera_png_base64:string|null;events:ReplayEvent[]}
export interface Sample {fly:Position;flyQuaternion?:Quaternion;obstacles:Position[];speed:number|null;worldIndex:number;decisionIndex:number;cameraIndex:number;encoderIndex:number;neuralIndex:number;neuralValues:number[]|null;channels:number[]|null;drive:number[]|null;encoderValid:boolean|null;score:number|null;sustained:number|null;gate:string;rule:string;decisionTime:number|null;neuralTime:number|null}
