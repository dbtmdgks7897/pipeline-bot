import yaml
from pathlib import Path


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config 파일이 없습니다: {path}\nconfig.yaml.example을 복사하여 config.yaml을 만드세요.")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_project_by_thread_id(config: dict, thread_id: int | None) -> dict | None:
    """thread_id로 프로젝트 이름과 경로를 반환. 없으면 None."""
    if thread_id is None:
        return None
    topics = config.get("telegram", {}).get("topics", {})
    for name, topic in topics.items():
        if topic.get("thread_id") == thread_id:
            return {
                "name": name,
                "path": Path(topic["project_path"]).expanduser().resolve(),
            }
    return None
