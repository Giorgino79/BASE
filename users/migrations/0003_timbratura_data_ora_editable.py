import datetime
from django.db import migrations, models
import users.models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_codice_fiscale_nullable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="timbratura",
            name="data",
            field=models.DateField(default=datetime.date.today, verbose_name="Data"),
        ),
        migrations.AlterField(
            model_name="timbratura",
            name="ora",
            field=models.TimeField(default=users.models._ora_default, verbose_name="Ora"),
        ),
    ]
