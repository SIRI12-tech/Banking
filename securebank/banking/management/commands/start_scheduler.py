from django.core.management.base import BaseCommand
from banking import scheduler

class Command(BaseCommand):
    help = 'Starts the APScheduler'

    def handle(self, *args, **options):
        scheduler.start()
        self.stdout.write(self.style.SUCCESS('Successfully started scheduler'))