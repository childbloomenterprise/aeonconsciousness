# SPDX-FileCopyrightText: Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
# Registration pattern adapted from NVIDIA's simple_web_query example.
# AEON-specific integration code is original; see THIRD_PARTY_NOTICES.md.
"""Expose AEON's bounded personal worker as a real NeMo toolkit workflow."""
import asyncio
import json
from pathlib import Path

from nat.plugin_api import Builder, FunctionBaseConfig, FunctionInfo, register_function
from pydantic import Field

from .models import ActionGrant, TaskSpec
from .runner import TaskRunner, TaskStore


class AEONWorkerConfig(FunctionBaseConfig, name="aeon_personal_worker"):
    workspace: str
    task_root: str | None = None
    grant_file: str | None = None
    deadline_minutes: int = Field(default=90, ge=1)
    max_model_tokens: int = Field(default=50_000, ge=1)
    max_steps: int = Field(default=32, ge=1)


@register_function(config_type=AEONWorkerConfig)
async def aeon_personal_worker(config: AEONWorkerConfig, builder: Builder):
    """NAT config, rather than model text, selects workspace and authority."""
    grant = ActionGrant.from_dict(json.loads(Path(config.grant_file).read_text(encoding="utf-8")) if config.grant_file else None)

    async def run(brief: str) -> str:
        spec = TaskSpec(brief=brief, workspace=str(Path(config.workspace).resolve()), grant=grant,
                        deadline_minutes=config.deadline_minutes, max_model_tokens=config.max_model_tokens,
                        max_steps=config.max_steps)
        runner = TaskRunner(TaskStore(Path(config.task_root) if config.task_root else None))
        # Playwright's synchronous API must run outside NAT's event-loop thread.
        result = await asyncio.to_thread(runner.start, spec)
        return json.dumps(result, ensure_ascii=False)

    yield FunctionInfo.from_fn(run, description="Complete a broad brief through AEON's checkpointed worker, grant checks and artifact verification.")
