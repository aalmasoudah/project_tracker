"""Record safe, idempotent backup or restoration-test verification metadata."""

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.operations.management.guards import (
    require_confirmation,
    require_exact_environment,
)
from apps.operations.policies import BACKUP_KINDS, OPERATION_STATUSES
from apps.operations.services import record_backup_verification


class Command(BaseCommand):
    help = (
        "Dry-run or record safe backup/restoration-test status. "
        "This command never reads or restores backup contents."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--environment", required=True)
        parser.add_argument("--kind", choices=BACKUP_KINDS, required=True)
        parser.add_argument("--status", choices=OPERATION_STATUSES, required=True)
        parser.add_argument("--completed-at", required=True)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Record the verification event; otherwise this is a dry-run.",
        )
        parser.add_argument("--confirm", default="")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        environment = str(options["environment"])
        kind = str(options["kind"])
        status = str(options["status"])
        require_exact_environment(environment)
        completed_at = parse_datetime(str(options["completed_at"]))
        if completed_at is None:
            raise CommandError("--completed-at must be an ISO-8601 datetime.")
        if timezone.is_naive(completed_at):
            completed_at = timezone.make_aware(completed_at)
        if completed_at > timezone.now() + timedelta(minutes=5):
            raise CommandError("--completed-at cannot be in the future.")
        summary = (
            f"environment={environment} kind={kind} status={status} "
            f"completed_at={completed_at.isoformat()}"
        )
        if not options["apply"]:
            self.stdout.write(f"DRY-RUN {summary}")
            return
        require_confirmation(
            provided=str(options["confirm"]),
            operation="RECORD-BACKUP-STATUS",
            environment=environment,
        )
        _event, created = record_backup_verification(
            kind=kind,
            environment=environment,
            status=status,
            completed_at=completed_at,
        )
        result = "recorded" if created else "already-recorded"
        self.stdout.write(self.style.SUCCESS(f"{result} {summary}"))
