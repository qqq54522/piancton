import asyncio
from threading import Event

from app.services.search_branch_runner import SearchBranchRunner


def test_search_branch_timeout_cancels_running_call():
    cancelled = Event()

    def blocking_call(signal):
        while not signal.cancelled:
            cancelled.wait(timeout=0.01)
        return "cancelled"

    result = asyncio.run(
        SearchBranchRunner().run_thread(
            "provider",
            blocking_call,
            timeout_seconds=0.02,
        )
    )

    assert result.diagnostic.status == "timed_out"
