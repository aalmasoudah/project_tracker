"""Approved Phase 14 operations and recovery constants."""

from typing import Final

RPO_HOURS: Final = 24
RTO_HOURS: Final = 8
BACKUP_RETENTION_DAYS: Final = 35
RESTORE_TEST_INTERVAL_DAYS: Final = 92
RETENTION_POLICY_CODE: Final = "indefinite"

DEPLOYMENT_ENVIRONMENTS: Final = (
    "development",
    "test",
    "staging",
    "production",
)
OPERATION_STATUSES: Final = ("succeeded", "failed")
BACKUP_KINDS: Final = ("backup", "restore_test")
