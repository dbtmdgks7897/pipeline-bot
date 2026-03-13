"""배치 리뷰 큐 — batch 승인 스텝 결과를 모아서 일괄 알림.

불변 패턴: add/flush 모두 새 인스턴스를 반환한다.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class BatchItem:
    project_name: str
    command: str
    message: str
    queued_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class BatchReviewQueue:
    _items: tuple[BatchItem, ...] = ()

    @property
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)

    def add(self, project_name: str, command: str, message: str) -> "BatchReviewQueue":
        item = BatchItem(
            project_name=project_name,
            command=command,
            message=message,
        )
        return BatchReviewQueue(_items=(*self._items, item))

    def flush(self) -> tuple[list[BatchItem], "BatchReviewQueue"]:
        items = list(self._items)
        return items, BatchReviewQueue()

    def format_summary(self) -> str:
        if self.is_empty:
            return ""

        lines = ["📋 배치 리뷰 요약\n"]
        for i, item in enumerate(self._items, 1):
            lines.append(
                f"{i}. [{item.project_name}] {item.command}\n"
                f"   {item.message[:200]}\n"
            )
        return "\n".join(lines)


# 모듈 레벨 싱글턴
_queue = BatchReviewQueue()


def enqueue(project_name: str, command: str, message: str) -> None:
    """배치 큐에 아이템을 추가한다. 모듈 변수를 교체."""
    global _queue
    _queue = _queue.add(project_name, command, message)


def flush_queue() -> list[BatchItem]:
    """큐를 비우고 아이템 목록을 반환한다."""
    global _queue
    items, _queue = _queue.flush()
    return items


def get_summary() -> str:
    """현재 큐의 요약을 반환한다."""
    return _queue.format_summary()


def is_empty() -> bool:
    """큐가 비어있는지 확인한다."""
    return _queue.is_empty
