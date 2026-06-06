from django.db import migrations


def create_class_ranks(apps, schema_editor):
    ClassRank = apps.get_model('users', 'ClassRank')
    ranks = [
        ('Unranked', 0),
        ('Copper III', 0),
        ('Copper II', 11),
        ('Copper I', 21),
        ('Bronze III', 31),
        ('Bronze II', 56),
        ('Bronze I', 82),
        ('Silver III', 108),
        ('Silver II', 159),
        ('Silver I', 210),
        ('Gold III', 261),
        ('Gold II', 362),
        ('Gold I', 463),
        ('Diamond III', 564),
        ('Diamond II', 815),
        ('Diamond I', 1066),
        ('Champion', 2000),
        ('Grand Champion', 3000),
        ('Master', 5000),
        ('Master of Masters', 10000),
    ]

    for name, xp in ranks:
        ClassRank.objects.update_or_create(name=name, defaults={'xp_threshold': xp})


def remove_class_ranks(apps, schema_editor):
    ClassRank = apps.get_model('users', 'ClassRank')
    names = [
        'Unranked', 'Copper III', 'Copper II', 'Copper I', 'Bronze III', 'Bronze II', 'Bronze I',
        'Silver III', 'Silver II', 'Silver I', 'Gold III', 'Gold II', 'Gold I',
        'Diamond III', 'Diamond II', 'Diamond I', 'Champion', 'Grand Champion', 'Master', 'Master of Masters'
    ]
    ClassRank.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_classrank'),
    ]

    operations = [
        migrations.RunPython(create_class_ranks, remove_class_ranks),
    ]
