"""Idempotent execution adapters and outcome-verification primitives."""

from app.execution.adapters import MockExecutionAdapter, VerificationEvaluator

__all__ = ["MockExecutionAdapter", "VerificationEvaluator"]
