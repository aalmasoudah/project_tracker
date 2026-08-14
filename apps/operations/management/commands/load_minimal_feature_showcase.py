"""Load the destructive minimal full-feature showcase after confirmation."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.operations.management.guards import (
    require_confirmation,
    require_exact_environment,
)
from apps.operations.showcase import build_minimal_feature_showcase


class Command(BaseCommand):
    help = (
        "Replace local development data with one compact Arabic full-feature "
        "scenario while retaining zx and the Telegram-bound demo.executive."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--environment", required=True)
        parser.add_argument("--demo-password", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm", default="")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        environment = str(options["environment"])
        require_exact_environment(environment)
        if environment != "development":
            raise CommandError(
                "The minimal feature showcase may run only in development."
            )
        if not options["apply"]:
            self.stdout.write(
                "DRY-RUN: would retain zx and demo.executive, replace local "
                "application data, and load the minimal full-feature showcase."
            )
            return
        require_confirmation(
            provided=str(options["confirm"]),
            operation="LOAD-MINIMAL-FEATURE-SHOWCASE",
            environment=environment,
        )
        password = str(options["demo_password"])
        try:
            summary = build_minimal_feature_showcase(password=password)
        except (RuntimeError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                "minimal-showcase-loaded "
                f"users={summary.users} projects={summary.projects} "
                f"courses={summary.courses} tasks={summary.tasks} "
                f"milestones={summary.milestones} trainees={summary.trainees} "
                f"sessions={summary.sessions} notifications={summary.notifications}"
            )
        )
