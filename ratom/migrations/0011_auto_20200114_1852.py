# Generated by Django 2.2.7 on 2020-01-14 23:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ratom", "0010_auto_20200114_1727"),
    ]

    operations = [
        migrations.RemoveField(model_name="message", name="msg_bcc",),
        migrations.RemoveField(model_name="message", name="msg_cc",),
    ]
