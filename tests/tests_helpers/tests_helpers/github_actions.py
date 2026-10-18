import os

import pytest


def annotate_failure(report: pytest.CollectReport | pytest.TestReport) -> None:
    if not report.failed or os.environ.get("GITHUB_ACTIONS") != "true":
        return
    message = f"{report.nodeid}\n{report.longrepr}"
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"\n::error::{message}", flush=True)  # noqa: T201


def pytest_collectreport(report):
    annotate_failure(report)


def pytest_runtest_logreport(report):
    annotate_failure(report)
