from django.core.management.base import BaseCommand
from django.utils.timezone import now
from Web.models import VotingCampaign, Nominee, Vote, Transaction
from decimal import Decimal
import random
from faker import Faker

fake = Faker()

class Command(BaseCommand):
    help = 'Create test votes for nominees'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=15, help='Number of votes to create')
        parser.add_argument('--nominee-id', type=int, default=None, help='Specific nominee ID')

    def handle(self, *args, **options):
        count = options['count']
        nominee_id = options['nominee_id']

        try:
            # Get campaign
            campaign = VotingCampaign.objects.filter(is_active=True).first()
            if not campaign:
                self.stdout.write(self.style.ERROR('No active campaign found'))
                return

            # Get nominees
            if nominee_id:
                nominees = Nominee.objects.filter(id=nominee_id, campaign=campaign)
            else:
                nominees = Nominee.objects.filter(campaign=campaign)

            if not nominees.exists():
                self.stdout.write(self.style.ERROR('No nominees found'))
                return

            created_count = 0
            for i in range(count):
                nominee = random.choice(list(nominees))
                vote_quantity = random.randint(1, 5)
                amount = Decimal(campaign.vote_price) * vote_quantity

                # Create vote
                vote = Vote.objects.create(
                    nominee=nominee,
                    voter_name=fake.name(),
                    voter_email=fake.email(),
                    voter_phone=fake.phone_number()[:20],
                    vote_quantity=vote_quantity,
                    amount=amount,
                    rest_points_earned=Decimal(campaign.rest_points_per_vote) * vote_quantity,
                    payment_status='paid'
                )

                # Create transaction
                Transaction.objects.create(
                    vote=vote,
                    reference=f'TEST_{vote.id}_{now().timestamp()}',
                    amount=amount,
                    status='success',
                    paid_at=now()
                )

                # Update nominee vote count
                nominee.vote_count = nominee.votes.count()
                nominee.save()

                created_count += 1

            self.stdout.write(self.style.SUCCESS(f'✓ Created {created_count} test votes'))
            
            # Show summary
            self.stdout.write('\n=== VOTING SUMMARY ===')
            for nominee in nominees:
                votes = nominee.votes.all()
                total_votes = votes.count()
                total_amount = sum(v.amount for v in votes)
                self.stdout.write(f'{nominee.name}: {total_votes} votes (₦{total_amount})')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
