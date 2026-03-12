from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_episode_task_queue'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='projectassetbinding',
            name='project_asse_project_5d0d77_idx',
        ),
        migrations.AddIndex(
            model_name='projectassetbinding',
            index=models.Index(fields=['project', 'created_at'], name='proj_asset_proj_created_idx'),
        ),
    ]
