"""Browser package init - Anti-Bot infrastructure."""

# Core anti-bot
from .anti_bot import (
    BrowserEmulator,
    RateLimiter,
    BrowserProfile,
    FetchResult,
    AntiBotConfig,
    JA3Spoofer,
    WAFDetector,
    WAFDetection,
    WAFType,
    SmartRetry,
)

# Orchestrator
from .orchestrator import FetchOrchestrator, Strategy, DomainSignal

# Executors
from .executors import (
    BaseFetchExecutor,
    FastExecutor,
    StrongExecutor,
    HeavyExecutor,
    ExecutorResult,
)

__all__ = [
    "BrowserEmulator",
    "RateLimiter",
    "BrowserProfile",
    "FetchResult",
    "AntiBotConfig",
    "JA3Spoofer",
    "WAFDetector",
    "WAFDetection",
    "WAFType",
    "SmartRetry",
    "FetchOrchestrator",
    "Strategy",
    "DomainSignal",
    "BaseFetchExecutor",
    "FastExecutor",
    "StrongExecutor",
    "HeavyExecutor",
    "ExecutorResult",
]