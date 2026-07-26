from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditevent",
            name="scope",
            field=models.CharField(
                choices=[
                    ("security", "Security"),
                    ("projects", "Projects"),
                ],
                db_index=True,
                default="security",
                max_length=32,
                verbose_name="scope",
            ),
        ),
    ]
