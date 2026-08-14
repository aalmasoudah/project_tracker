from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "project_agents",
            "0005_agentproposal_project_agents_proposal_action_valid_and_more",
        ),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="agentrun",
            name="project_agents_model_valid",
        ),
        migrations.AddConstraint(
            model_name="agentrun",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    model_code__in=(
                        "openai/gpt-oss-20b",
                        "openai/gpt-oss-120b",
                        "qwen/qwen3.5-9b",
                    )
                ),
                name="project_agents_model_valid",
            ),
        ),
    ]
