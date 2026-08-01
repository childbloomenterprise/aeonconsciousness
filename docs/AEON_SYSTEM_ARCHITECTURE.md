# System Architecture

```text
Researcher → FastAPI → AeonRuntime → Manas → Attention → Workspace
                                      ↓                 ↓
                                  Chitta ← recurrence → Self/World model
                                      ↓                 ↓
                                 Metacognition → Buddhi → Ahamkara → response
                                      │                              │
                                      └──── signed event stream ─────┘
                                                  ↓
                              Sakshin + Model Behaviour Observer
                                                  ↓
                                    React Research Console
```

Local JSON/JSONL is authoritative. Supabase is an optional mirror behind an adapter. Provider identity is separate from AEON continuity identity.

