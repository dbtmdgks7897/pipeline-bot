"""프로젝트별 동시 실행 방지 — 같은 프로젝트에서 중복 실행 차단."""


class ProjectLock:
    """프로젝트 이름 기반 비동기 Lock 관리자.

    같은 프로젝트에서 동시에 claude를 실행하면 충돌하므로,
    프로젝트당 하나의 실행만 허용한다.
    """

    def __init__(self) -> None:
        self._locked: set[str] = set()

    def is_locked(self, project_name: str) -> bool:
        return project_name in self._locked

    async def acquire(self, project_name: str) -> bool:
        """Lock 획득 시도. 이미 잠겨있으면 False 반환."""
        if project_name in self._locked:
            return False
        self._locked.add(project_name)
        return True

    def release(self, project_name: str) -> None:
        """Lock 해제. 없으면 무시."""
        self._locked.discard(project_name)

    def running_projects(self) -> list[str]:
        """현재 실행 중인 프로젝트 목록."""
        return sorted(self._locked)
