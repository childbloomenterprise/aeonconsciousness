import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function TelemetryChart({data}: {data: Array<{index: number; confidence: number; activity: number}>}) {
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><defs><linearGradient id="confidence" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#62e6c5" stopOpacity={.4}/><stop offset="1" stopColor="#62e6c5" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#1c2732" vertical={false}/><XAxis dataKey="index" hide/><YAxis domain={[0,100]} tick={{fill:'#73808d',fontSize:11}}/><Tooltip contentStyle={{background:'#0c1218',border:'1px solid #24313d'}}/><Area type="monotone" dataKey="confidence" stroke="#62e6c5" fill="url(#confidence)"/></AreaChart></ResponsiveContainer>
}
