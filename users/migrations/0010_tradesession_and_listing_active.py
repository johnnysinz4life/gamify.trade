from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_directmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='TradeSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('CLOSED_PRE_TRADE', 'Closed (pre-trade)'), ('CONCLUDED_AWAITING_RATING', 'Concluded (awaiting rating)'), ('CONCLUDED_FINAL', 'Concluded (final)'), ('EXPIRED_INACTIVE', 'Expired (inactive)')], default='ACTIVE', max_length=32)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_activity_at', models.DateTimeField(auto_now=True)),
                ('close_a_confirmed', models.BooleanField(default=False)),
                ('close_b_confirmed', models.BooleanField(default=False)),
                ('close_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('conclude_a_confirmed', models.BooleanField(default=False)),
                ('conclude_b_confirmed', models.BooleanField(default=False)),
                ('conclude_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('a_rating', models.CharField(blank=True, choices=[('GOOD', 'Good'), ('GREAT', 'Great'), ('BAD', 'Bad'), ('TERRIBLE', 'Terrible')], max_length=16, null=True)),
                ('b_rating', models.CharField(blank=True, choices=[('GOOD', 'Good'), ('GREAT', 'Great'), ('BAD', 'Bad'), ('TERRIBLE', 'Terrible')], max_length=16, null=True)),
                ('xp_awarded_a_to_other', models.BooleanField(default=False)),
                ('xp_awarded_b_to_other', models.BooleanField(default=False)),
                ('concluded_final_at', models.DateTimeField(blank=True, null=True)),
                ('user_a', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trade_sessions_a', to='auth.user')),
                ('user_b', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trade_sessions_b', to='auth.user')),

            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='tradesession',
            constraint=models.UniqueConstraint(fields=('user_a', 'user_b'), name='unique_trade_session_per_pair_unordered'),
        ),
        migrations.AddConstraint(
            model_name='tradesession',
            constraint=models.CheckConstraint(check=~models.Q(user_a=models.F('user_b')), name='trade_users_must_be_different'),
        ),
    ]

