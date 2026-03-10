from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0003_add_skipped_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Series',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='作品名称')),
                ('description', models.TextField(blank=True, verbose_name='作品描述')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='series_projects', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '作品',
                'verbose_name_plural': '作品',
                'db_table': 'series',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='project',
            name='episode_number',
            field=models.IntegerField(blank=True, null=True, verbose_name='分集序号'),
        ),
        migrations.AddField(
            model_name='project',
            name='episode_title',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='分集标题'),
        ),
        migrations.AddField(
            model_name='project',
            name='series',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='episodes', to='projects.series', verbose_name='所属作品'),
        ),
        migrations.AddField(
            model_name='project',
            name='sort_order',
            field=models.IntegerField(default=0, verbose_name='排序值'),
        ),
        migrations.AddIndex(
            model_name='series',
            index=models.Index(fields=['user', '-created_at'], name='series_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['series', 'sort_order', 'episode_number'], name='projects_series_sort_idx'),
        ),
    ]
