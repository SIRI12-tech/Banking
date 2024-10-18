# Generated by Django 5.1.2 on 2024-10-14 00:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('banking', '0002_transaction_reference_number_transaction_to_account_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='email_verification_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='is_email_verified',
            field=models.BooleanField(default=False),
        ),
    ]
