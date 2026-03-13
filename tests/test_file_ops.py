import pytest
import tempfile
from pathlib import Path

from src.file_ops import save_md_to_todo


@pytest.fixture
def project_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSaveMdToTodo:
    def test_creates_file_with_md_extension(self, project_dir):
        path = save_md_to_todo(project_dir, "feature-x", "# 내용")
        assert path.exists()
        assert path.suffix == ".md"
        assert path.name == "feature-x.md"

    def test_does_not_double_md_extension(self, project_dir):
        path = save_md_to_todo(project_dir, "feature-x.md", "# 내용")
        assert path.name == "feature-x.md"

    def test_saves_correct_content(self, project_dir):
        content = "# 제목\n\n본문 내용입니다."
        path = save_md_to_todo(project_dir, "test", content)
        assert path.read_text(encoding="utf-8") == content

    def test_creates_mymd_todo_directory(self, project_dir):
        save_md_to_todo(project_dir, "test", "내용")
        assert (project_dir / "mymd" / "todo").is_dir()

    def test_places_file_in_mymd_todo(self, project_dir):
        path = save_md_to_todo(project_dir, "test", "내용")
        assert path.parent == project_dir / "mymd" / "todo"

    def test_overwrites_existing_file(self, project_dir):
        save_md_to_todo(project_dir, "test", "이전 내용")
        path = save_md_to_todo(project_dir, "test", "새 내용")
        assert path.read_text(encoding="utf-8") == "새 내용"

    def test_handles_unicode_content(self, project_dir):
        content = "# 한국어 내용\n이모지 🚀 포함"
        path = save_md_to_todo(project_dir, "unicode-test", content)
        assert path.read_text(encoding="utf-8") == content
