import pytest
from datetime import datetime

from src.batch_review import BatchItem, BatchReviewQueue, enqueue, flush_queue, is_empty
import src.batch_review as batch_mod


class TestBatchReviewQueue:
    def test_starts_empty(self):
        queue = BatchReviewQueue()
        assert queue.is_empty is True
        assert len(queue) == 0

    def test_add_returns_new_queue(self):
        queue = BatchReviewQueue()
        new_queue = queue.add("kigaru", "tdd", "테스트 통과")

        assert len(new_queue) == 1
        assert len(queue) == 0  # 원본 불변

    def test_add_multiple_items(self):
        queue = BatchReviewQueue()
        queue = queue.add("kigaru", "tdd", "테스트 통과")
        queue = queue.add("kigaru", "code-review", "리뷰 완료")

        assert len(queue) == 2

    def test_flush_returns_items_and_empty_queue(self):
        queue = BatchReviewQueue()
        queue = queue.add("kigaru", "tdd", "테스트 통과")
        queue = queue.add("imysh", "code-review", "리뷰 완료")

        items, new_queue = queue.flush()

        assert len(items) == 2
        assert new_queue.is_empty is True
        assert len(queue) == 2  # 원본 불변

    def test_format_summary(self):
        queue = BatchReviewQueue()
        queue = queue.add("kigaru", "tdd", "테스트 5개 통과")
        queue = queue.add("kigaru", "code-review", "이슈 없음")

        summary = queue.format_summary()

        assert "kigaru" in summary
        assert "tdd" in summary
        assert "code-review" in summary

    def test_format_summary_empty(self):
        queue = BatchReviewQueue()
        summary = queue.format_summary()
        assert summary == ""


class TestModuleFunctions:
    def setup_method(self):
        """각 테스트 전 큐 초기화."""
        batch_mod._queue = BatchReviewQueue()

    def test_enqueue_and_flush(self):
        enqueue("kigaru", "tdd", "통과")
        enqueue("kigaru", "review", "완료")

        assert not is_empty()
        items = flush_queue()

        assert len(items) == 2
        assert items[0].command == "tdd"
        assert is_empty()

    def test_enqueue_persists_across_calls(self):
        enqueue("kigaru", "tdd", "통과")
        assert not is_empty()
        enqueue("imysh", "review", "완료")

        items = flush_queue()
        assert len(items) == 2
