import django.contrib.postgres.constraints
import django.db.models.deletion
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("salas", "0001_initial"),
    ]

    operations = [
        BtreeGistExtension(),
        
        # ✅ Crear el tipo ANTES del modelo
        migrations.RunSQL(
            sql="CREATE TYPE timerange AS RANGE (subtype = time);",
            reverse_sql="DROP TYPE timerange;",
        ),
        
        migrations.CreateModel(
            name="Horario",
            fields=[
                ("id_horario", models.AutoField(primary_key=True, serialize=False)),
                ("dia_semana", models.IntegerField(choices=[
                    (1, "Lunes"), (2, "Martes"), (3, "Miércoles"),
                    (4, "Jueves"), (5, "Viernes"), (6, "Sábado"), (7, "Domingo"),
                ])),
                ("hora_inicio", models.TimeField()),
                ("hora_fin", models.TimeField()),
                ("sala", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="horarios",
                    to="salas.sala",
                )),
            ],
            options={
                "constraints": [
                    django.contrib.postgres.constraints.ExclusionConstraint(
                        expressions=[
                            ("sala", "="),
                            ("dia_semana", "="),
                            (models.Func("hora_inicio", "hora_fin", function="timerange"), "&&"),
                        ],
                        name="exclude_overlapping_reservations",
                    )
                ],
            },
        ),
    ]