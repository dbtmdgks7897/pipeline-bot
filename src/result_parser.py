from src.claude_runner import ClaudeResult

MAX_TELEGRAM_LEN = 4096
_TRUNCATION_SUFFIX = "\n...(잘림)"


def parse_claude_output(result: ClaudeResult, command: str, project_name: str) -> str:
    """Claude 출력을 Telegram 메시지 형식으로 변환. 4096자 이내.

    메시지가 4096자를 초과하면 body의 끝부분만 남기고 '잘림'을 표시한다.
    """
    if result.success:
        header = f"🔧 {project_name} — {command} 완료\n\n"
        body = result.output
    else:
        header = f"❌ {project_name} — {command} 실패\n\n"
        body = result.error

    message = header + body

    if len(message) > MAX_TELEGRAM_LEN:
        available = MAX_TELEGRAM_LEN - len(header) - len(_TRUNCATION_SUFFIX)
        truncated_body = body[-max(available, 0):]
        message = header + truncated_body + _TRUNCATION_SUFFIX

    return message
