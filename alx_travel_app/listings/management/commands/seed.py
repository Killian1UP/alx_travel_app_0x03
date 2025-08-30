import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from listings.models import Listing

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample listings'

    def handle(self, *args, **kwargs):
        # Create a host user if not exists
        host, created = User.objects.get_or_create(
            username='samplehost',
            defaults={'email': 'host@example.com', 'password': 'testpass123'}
        )

        # Sample data
        sample_listings = [
            {
                'title': 'Cozy Cottage',
                'description': 'A cozy cottage in the woods.',
                'location': 'Cape Town',
                'price_per_night': 500.00,
                'max_guests': 4,
            },
            {
                'title': 'Modern Apartment',
                'description': 'A modern apartment near the beach.',
                'location': 'Durban',
                'price_per_night': 750.00,
                'max_guests': 2,
            },
            {
                'title': 'Luxury Villa',
                'description': 'A luxurious villa with pool and sea view.',
                'location': 'Johannesburg',
                'price_per_night': 1500.00,
                'max_guests': 6,
            },
        ]

        for data in sample_listings:
            listing, created = Listing.objects.get_or_create(
                title=data['title'],
                defaults={
                    'host': host,
                    'description': data['description'],
                    'location': data['location'],
                    'price_per_night': data['price_per_night'],
                    'max_guests': data['max_guests'],
                    'is_available': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created listing: {listing.title}"))
            else:
                self.stdout.write(f"Listing already exists: {listing.title}")
