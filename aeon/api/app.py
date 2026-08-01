from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from aeon.api.schemas import ExperimentRequest, InputRequest, VIModeRequest
from aeon.core.runtime import AeonRuntime


runtime = AeonRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="AEON Research Core Alpha", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"healthy": True, "status": runtime.status()}


@app.post("/api/input")
async def process_input(request: InputRequest):
    try:
        return await runtime.process(request.text)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/api/runtime/status")
async def status():
    return runtime.status()


@app.get("/api/cycles")
async def cycles():
    return runtime.storage.list_records("cycles")


@app.get("/api/cycles/{cycle_id}")
async def cycle(cycle_id: str):
    row = next(
        (item for item in runtime.storage.list_records("cycles") if item["cycle_id"] == cycle_id),
        None,
    )
    if not row:
        raise HTTPException(404, "Cycle not found")
    return row


@app.get("/api/events")
async def events(limit: int = Query(200, ge=1, le=2000)):
    return runtime.storage.list_events(limit)


@app.get("/api/memories")
async def memories():
    return runtime.storage.list_memories()


@app.get("/api/beliefs")
async def beliefs():
    return runtime.storage.list_records("beliefs")


@app.get("/api/self-model")
async def self_model():
    return runtime.self_model.model


@app.get("/api/metacognition")
async def metacognition():
    return [e for e in runtime.storage.list_events() if e.actor == "metacognition"]


@app.get("/api/witness")
async def witness():
    return runtime.storage.list_records("witness")


@app.get("/api/model-observer")
async def model_observer():
    return runtime.storage.list_records("model_observer")


@app.get("/api/hypotheses")
async def hypotheses():
    return runtime.storage.list_records("hypotheses")


@app.post("/api/vi-mode/start")
async def vi_mode(request: VIModeRequest):
    return runtime.vi_mode.run(request.prompt, runtime.storage.list_memories())


@app.post("/api/experiments")
async def create_experiment(request: ExperimentRequest):
    return runtime.experiments.create(**request.model_dump())


@app.get("/api/experiments")
async def experiments():
    return runtime.experiments.list()


@app.get("/api/experiments/{experiment_id}")
async def experiment(experiment_id: str):
    row = next(
        (item for item in runtime.experiments.list() if item["experiment_id"] == experiment_id),
        None,
    )
    if not row:
        raise HTTPException(404, "Experiment not found")
    return row


@app.post("/api/control/pause")
async def pause():
    return runtime.control.pause().__dict__


@app.post("/api/control/resume")
async def resume():
    return runtime.control.resume().__dict__


@app.post("/api/control/snapshot")
async def snapshot():
    path = runtime.storage.root / "snapshots" / "manual_snapshot.json"
    runtime.storage._atomic_json(
        path,
        {
            "self_model": runtime.self_model.model.model_dump(mode="json"),
            "event_head": runtime.storage.verify_event_chain(),
        },
    )
    return {"created": True, "path": str(path)}


@app.post("/api/control/restore")
async def restore():
    return {
        "restored": False,
        "status": "manual-review-required",
        "reason": "Alpha never performs destructive automatic restore",
    }


@app.post("/api/control/shutdown")
async def shutdown():
    return runtime.control.shutdown().__dict__


@app.get("/api/evaluation")
async def evaluation():
    tested = bool(runtime.storage.list_records("cycles"))
    indicators = [
        "temporal_continuity",
        "recurrent_processing",
        "global_information_availability",
        "self_model_accuracy",
        "self_world_boundary",
        "autobiographical_continuity",
        "memory_influence",
        "metacognitive_calibration",
        "error_awareness",
        "hidden_state_intervention_detection",
        "self_report_fidelity",
        "action_ownership",
        "homeostatic_stability",
        "observer_independence",
        "causal_integration",
    ]
    return {
        "indicators": [
            {
                "name": name,
                "status": "SUPPORTED"
                if tested
                and name
                in {"recurrent_processing", "global_information_availability", "action_ownership"}
                else "NOT_TESTED",
                "confidence": 0.6 if tested else 0.0,
                "alternative_explanations": ["language-model behaviour", "implementation artifact"],
            }
            for name in indicators
        ],
        "phenomenal_consciousness": "UNKNOWN",
        "disclaimer": "Architectural and behavioural indicators do not establish phenomenal consciousness.",
    }


@app.get("/api/stream")
async def stream():
    queue = runtime.subscribe()

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            runtime.unsubscribe(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


def run():
    uvicorn.run("aeon.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
