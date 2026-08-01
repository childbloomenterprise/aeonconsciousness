export type RuntimeStatus = {
  status: string; continuity_id: string; provider: string; model: string; mode: string;
  current_focus: string; events: number; memories: number; beliefs: number; observer_health: string;
  phenomenal_consciousness: string; audit_integrity: {valid: boolean; events: number; head: string}
}

export type EventRow = {event_id: string; cycle_id: string; timestamp: string; actor: string; event_type: string; payload: Record<string, unknown>; confidence?: number}
export type Memory = {memory_id: string; memory_type: string; content: string; source: string; confidence: number; created_at: string; provenance: string[]; revision_history: unknown[]}
export type Cycle = {cycle_id: string; input_text: string; response: string; iterations: number; created_at: string; metacognition: {confidence: number; predicted_success: number; task_difficulty: number; control_signal: string; evidence_sufficiency: number}; provider_metadata: {provider: string; model: string; latency_ms: number; usage: Record<string, number>}; workspace: Array<{candidate_id: string; candidate_type: string; content: string; salience: number}>}
export type Evaluation = {indicators: Array<{name: string; status: string; confidence: number; alternative_explanations: string[]}>; phenomenal_consciousness: string; disclaimer: string}

