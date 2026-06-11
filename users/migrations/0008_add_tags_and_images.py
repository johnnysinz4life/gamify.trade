from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_populate_classranks'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=40, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='listing',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='listings', to='users.Tag'),
        ),
        migrations.CreateModel(
            name='ListingImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='listing_photos/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('listing', models.ForeignKey(on_delete=models.CASCADE, related_name='images', to='users.listing')),
            ],
        ),
    ]
