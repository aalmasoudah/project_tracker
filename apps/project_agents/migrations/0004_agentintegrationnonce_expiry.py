from django.db import migrations, models
from django.utils import timezone


def expire_existing_nonces(apps, schema_editor) -> None:
    del schema_editor
    nonce_model = apps.get_model("project_agents", "AgentIntegrationNonce")
    nonce_model.objects.filter(expires_at__isnull=True).update(
        expires_at=timezone.now()
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "project_agents",
            "0003_remove_agentproposal_project_agents_proposal_decision_valid_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="agentintegrationnonce",
            name="expires_at",
            field=models.DateTimeField(db_index=True, null=True),
        ),
        migrations.RunPython(expire_existing_nonces, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="agentintegrationnonce",
            name="expires_at",
            field=models.DateTimeField(db_index=True),
        ),
        migrations.AlterModelOptions(
            name="agentintegrationnonce",
            options={"ordering": ("expires_at",)},
        ),
    ]
