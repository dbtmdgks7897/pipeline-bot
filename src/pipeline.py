"""파이프라인 세션 관리 + 체인 실행 엔진.

/pipeline 명령으로 시작되는 자동 체인을 관리한다.
trust_level에 따라 auto/required/batch로 흐름을 제어한다.
"""

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Awaitable

from src.claude_runner import ClaudeResult, run_claude
from src.result_parser import parse_claude_output


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_APPROVAL = "waiting_approval"


@dataclass(frozen=True)
class PipelineStep:
    command: str
    approve: str  # "auto" | "required" | "batch"
    status: StepStatus = StepStatus.PENDING
    result: ClaudeResult | None = None

    def with_status(self, status: StepStatus, result: ClaudeResult | None = None) -> "PipelineStep":
        return PipelineStep(
            command=self.command,
            approve=self.approve,
            status=status,
            result=result,
        )


# send_fn 타입: async (str, keyboard | None) -> None
SendFn = Callable[[str, object], Awaitable[None]]


@dataclass(frozen=True)
class PipelineSession:
    session_id: str
    project: dict
    steps: tuple[PipelineStep, ...]
    current_index: int = 0

    @property
    def current_step(self) -> PipelineStep | None:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.steps)

    def advance(self) -> "PipelineSession":
        return PipelineSession(
            session_id=self.session_id,
            project=self.project,
            steps=self.steps,
            current_index=self.current_index + 1,
        )

    def _replace_current_step(self, new_step: PipelineStep) -> "PipelineSession":
        steps = list(self.steps)
        steps[self.current_index] = new_step
        return PipelineSession(
            session_id=self.session_id,
            project=self.project,
            steps=tuple(steps),
            current_index=self.current_index,
        )

    async def execute_next(self, send_fn: SendFn) -> "PipelineSession":
        """현재 스텝을 실행하고 결과에 따라 세션을 반환한다.

        - auto: 실행 → 성공 시 다음 스텝으로 재귀
        - required: 승인 버튼 전송 후 멈춤
        - batch: 실행 → 결과 큐 적재 → 다음 스텝으로 재귀
        """
        step = self.current_step
        if step is None:
            await send_fn(
                f"✅ {self.project['name']} — 파이프라인 완료 "
                f"({len(self.steps)}개 스텝)",
                None,
            )
            return self

        if step.approve == "required":
            updated = self._replace_current_step(
                step.with_status(StepStatus.WAITING_APPROVAL)
            )
            progress = f"[{self.current_index + 1}/{len(self.steps)}]"
            await send_fn(
                f"⏸ {progress} {self.project['name']} — {step.command}\n"
                f"승인이 필요합니다.",
                {"type": "pipeline_approval", "session_id": self.session_id},
            )
            return updated

        # auto 또는 batch: 실행
        progress = f"[{self.current_index + 1}/{len(self.steps)}]"
        await send_fn(
            f"⏳ {progress} {self.project['name']} — {step.command} 실행 중...",
            None,
        )

        result = await run_claude(step.command, self.project["path"])

        if not result.success:
            failed_step = step.with_status(StepStatus.FAILED, result)
            failed_session = self._replace_current_step(failed_step)
            message = parse_claude_output(result, step.command, self.project["name"])
            await send_fn(f"❌ {progress} 파이프라인 중단\n\n{message}", None)
            return failed_session

        completed_step = step.with_status(StepStatus.COMPLETED, result)
        completed_session = self._replace_current_step(completed_step).advance()

        message = parse_claude_output(result, step.command, self.project["name"])

        if step.approve == "batch":
            from src.batch_review import enqueue
            enqueue(self.project["name"], step.command, message)
            await send_fn(f"📦 {progress} 배치 큐 적재 — {step.command}", None)
        else:
            await send_fn(f"✅ {progress} {message}", None)

        return await completed_session.execute_next(send_fn)


def create_session(config: dict, project: dict) -> PipelineSession:
    """config.yaml의 pipelines.default에서 세션을 생성한다."""
    raw_steps = config.get("pipelines", {}).get("default", [])
    steps = tuple(
        PipelineStep(command=s["step"], approve=s["approve"])
        for s in raw_steps
    )
    return PipelineSession(
        session_id=uuid.uuid4().hex[:8],
        project=project,
        steps=steps,
    )
