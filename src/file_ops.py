from pathlib import Path


def save_md_to_todo(project_path: Path, filename: str, content: str) -> Path:
    """프로젝트의 mymd/todo/에 md 파일을 직접 생성한다.

    Args:
        project_path: 프로젝트 루트 경로
        filename: 저장할 파일명 (.md 없어도 자동 추가)
        content: 파일 내용

    Returns:
        생성된 파일의 절대 경로
    """
    if not filename.endswith(".md"):
        filename = filename + ".md"

    todo_dir = project_path / "mymd" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    filepath = todo_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath
