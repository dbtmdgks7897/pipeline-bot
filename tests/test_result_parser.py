from src.claude_runner import ClaudeResult
from src.result_parser import parse_claude_output


def make_result(success=True, output="", error="", exit_code=0, elapsed=1.0):
    return ClaudeResult(success=success, output=output, error=error, exit_code=exit_code, elapsed=elapsed)


class TestParseClaudeOutput:
    def test_success_format_has_project_command_and_done(self):
        result = make_result(output="작업 완료")
        msg = parse_claude_output(result, "plan-sync", "kigaru")
        assert "🔧" in msg
        assert "kigaru" in msg
        assert "plan-sync" in msg
        assert "완료" in msg

    def test_failure_format_has_error_indicator(self):
        result = make_result(success=False, error="Command not found", exit_code=1)
        msg = parse_claude_output(result, "bad-cmd", "kigaru")
        assert "❌" in msg
        assert "실패" in msg
        assert "Command not found" in msg

    def test_output_over_4096_gets_truncated(self):
        long_output = "x" * 5000
        result = make_result(output=long_output)
        msg = parse_claude_output(result, "cmd", "proj")
        assert len(msg) <= 4096
        assert "잘림" in msg

    def test_short_output_not_truncated(self):
        result = make_result(output="짧은 출력")
        msg = parse_claude_output(result, "cmd", "proj")
        assert len(msg) <= 4096
        assert "잘림" not in msg
        assert "짧은 출력" in msg

    def test_success_includes_output_content(self):
        result = make_result(output="3개 항목 추가됨")
        msg = parse_claude_output(result, "plan-sync", "kigaru")
        assert "3개 항목 추가됨" in msg

    def test_long_output_keeps_last_part(self):
        long_output = "BEGINNING" + "x" * 3000 + "END_MARKER"
        result = make_result(output=long_output)
        msg = parse_claude_output(result, "cmd", "proj")
        assert "END_MARKER" in msg

    def test_failure_includes_error_content(self):
        result = make_result(success=False, error="권한 없음: /root", exit_code=1)
        msg = parse_claude_output(result, "cmd", "proj")
        assert "권한 없음: /root" in msg

    def test_timeout_error_shown_in_failure(self):
        result = make_result(success=False, error="실행 타임아웃 (300초 초과)", exit_code=-1)
        msg = parse_claude_output(result, "tdd", "myproject")
        assert "타임아웃" in msg
