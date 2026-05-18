import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model

# point this to your Django project settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postit.settings")

django.setup()

# Run migrations
call_command("makemigrations")
call_command("migrate")

User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin",
        email="thefarmerpoint06@gmail.com",
        password="Pak-System123"
    )
    print("Superuser 'admin' created")
else:
    print("Superuser already exists")
