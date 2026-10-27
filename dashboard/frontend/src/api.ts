export const API_BASE=(import.meta.env.VITE_API_BASE as string|undefined)?.replace(/\/$/,'')??'';
export const apiURL=(path:string)=>`${API_BASE}${path}`;
export function wsURL(path:string){const url=new URL(apiURL(path),window.location.href);url.protocol=url.protocol==='https:'?'wss:':'ws:';return url.toString()}
export async function get<T>(path:string,signal?:AbortSignal):Promise<T>{const response=await fetch(apiURL(path),{signal});if(!response.ok){let message=`Data service returned ${response.status}`;try{const value=await response.json();message=String(value.detail??message)}catch{/* preserve HTTP status */}throw new Error(message)}return response.json() as Promise<T>}
