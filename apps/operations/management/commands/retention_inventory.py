"""Report the approved non-destructive retention scope."""

import hashlib
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.operations.management.guards import (
    require_confirmation,
    require_exact_environment,
)
from apps.operations.services import (
    record_retention_inventory,
    retention_inventory,
)


class Command(BaseCommand):
    help = (
        "Report protected records under the indefinite-retention policy. "
        "This command has no deletion mode."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--environment", required=True)
        parser.add_argument(
            "--record",
            action="store_true",
            help="Record an idempotent safe summary after printing the inventory.",
        )
        parser.add_argument("--confirm", default="")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        environment = str(options["environment"])
        require_exact_environment(environment)
        inventory = retention_inventory()
        payload = {
            "deletion_candidates": inventory.deletion_candidates,
            "environment": environment,
            "policy": inventory.policy,
            "protected_models": inventory.counts,
            "total_records": inventory.total_records,
        }
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.stdout.write(serialized)
        if not options["record"]:
            self.stdout.write("DRY-RUN: no data was changed; no deletion mode exists.")
            return
        require_confirmation(
            provided=str(options["confirm"]),
            operation="RECORD-RETENTION-INVENTORY",
            environment=environment,
        )
        operation_key = hashlib.sha256(serialized.encode()).hexdigest()
        _event, created = record_retention_inventory(
            environment=environment,
            inventory=inventory,
            operation_key=operation_key,
        )
        result = "recorded" if created else "already-recorded"
        self.stdout.write(self.style.SUCCESS(result))
