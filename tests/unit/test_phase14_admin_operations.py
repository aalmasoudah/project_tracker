"""Focused Phase 14 policy, redaction, and command-guard tests."""

from datetime import timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from django import forms
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.forms import AuditFilterForm
from apps.audit.models import AuditEvent
from apps.audit.selectors import safe_audit_metadata
from apps.operations.management.guards import (
    require_confirmation,
    require_exact_environment,
)


def actor_with_permissions(*allowed: str) -> User:
    actor = Mock(spec=User)
    actor.has_perm.side_effect = lambda permission: permission in allowed
    return cast(User, actor)


@pytest.mark.unit
def test_audit_filter_choices_are_permission_scoped_and_bounded() -> None:
    actor = actor_with_permissions("audit.view_security_audit")
    today = timezone.localdate()
    form = AuditFilterForm(
        actor,
        {
            "scope": "projects",
            "date_from": today - timedelta(days=400),
            "date_to": today,
        },
    )

    assert not form.is_valid()
    scope_field = cast(forms.ChoiceField, form.fields["scope"])
    assert "projects" not in {code for code, _label in scope_field.choices}


@pytest.mark.unit
def test_audit_metadata_requires_an_explicit_safe_key() -> None:
    event = cast(
        AuditEvent,
        SimpleNamespace(
            metadata={
                "status": "active",
                "password": "must-not-render",
                "name": "private-filename.pdf",
                "nested_unknown": {"secret": "must-not-render"},
            }
        ),
    )

    assert safe_audit_metadata(event) == {"status": "active"}


@pytest.mark.unit
@override_settings(DEPLOYMENT_ENVIRONMENT="staging")
def test_command_guards_require_exact_environment_and_confirmation() -> None:
    require_exact_environment("staging")
    require_confirmation(
        provided="RECORD-BACKUP-STATUS:staging",
        operation="RECORD-BACKUP-STATUS",
        environment="staging",
    )
    with pytest.raises(CommandError):
        require_exact_environment("production")
    with pytest.raises(CommandError):
        require_confirmation(
            provided="yes",
            operation="RECORD-BACKUP-STATUS",
            environment="staging",
        )
