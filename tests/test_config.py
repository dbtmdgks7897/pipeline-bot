import pytest
import tempfile
import yaml
from pathlib import Path

from src.config import load_config, get_project_by_thread_id


@pytest.fixture
def sample_config():
    return {
        "telegram": {
            "bot_token": "test-token",
            "group_id": -100123456,
            "topics": {
                "kigaru": {
                    "thread_id": 123,
                    "project_path": "/Users/ysh/dev/kigaru",
                },
                "imysh": {
                    "thread_id": 456,
                    "project_path": "/Users/ysh/dev/imysh",
                },
            },
        }
    }


@pytest.fixture
def config_file(sample_config):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_config, f)
        return f.name


class TestLoadConfig:
    def test_loads_valid_config(self, config_file):
        config = load_config(config_file)
        assert config["telegram"]["bot_token"] == "test-token"
        assert config["telegram"]["group_id"] == -100123456

    def test_raises_on_missing_file(self):
        with pytest.raises(FileNotFoundError, match="config 파일이 없습니다"):
            load_config("nonexistent.yaml")


class TestGetProjectByThreadId:
    def test_returns_project_for_known_thread_id(self, sample_config):
        project = get_project_by_thread_id(sample_config, 123)
        assert project is not None
        assert project["name"] == "kigaru"
        assert isinstance(project["path"], Path)

    def test_returns_none_for_unknown_thread_id(self, sample_config):
        project = get_project_by_thread_id(sample_config, 999)
        assert project is None

    def test_returns_none_for_none_thread_id(self, sample_config):
        project = get_project_by_thread_id(sample_config, None)
        assert project is None

    def test_second_topic_mapping(self, sample_config):
        project = get_project_by_thread_id(sample_config, 456)
        assert project is not None
        assert project["name"] == "imysh"
