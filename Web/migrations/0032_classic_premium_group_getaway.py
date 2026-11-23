from decimal import Decimal

from django.db import migrations


PREMIUM = {
    'name': 'Classic Premium',
    'category': 'group',
    'experience_duration': 'one_day',
    'pricing_basis': 'person',
    'included_adults': 1,
    'included_children': 0,
    'price_per_person': Decimal('120000.00'),
    'tagline': 'A more considered day at the beach.',
    'short_description': 'An elevated private beach escape, with thoughtful touches of relaxation and indulgence.',
    'description': (
        'An elevated private beach escape, with thoughtful touches of relaxation and indulgence. '
        'Make a day of the coast, with time to settle in, enjoy a massage, and take in considered '
        'manicure and pedicure services at your own pace.'
    ),
    'who_is_it_for': 'Groups looking for a more elevated day away.\nFriends and colleagues who value time to relax together.',
    'inclusions': 'Private beach escape\nResort experience\nMassage\nManicure\nPedicure',
    'is_active': True,
    'instalment_charge_percent': Decimal('0'),
    'instalment_charge_flat': Decimal('0'),
    'available_durations': '3,6,9,12',
}

CLASSIC = {
    'name': 'Classic',
    'category': 'group',
    'experience_duration': 'one_day',
    'pricing_basis': 'person',
    'price_per_person': Decimal('50000.00'),
    'tagline': 'A refreshing group beach getaway filled with relaxation, fun, food and connection.',
    'short_description': 'A refreshing group beach getaway filled with relaxation, fun, food and connection.',
    'is_active': True,
}


def create_classic_premium(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    Package.objects.update_or_create(slug='classic-premium', defaults=PREMIUM)
    Package.objects.filter(slug='classic').update(**CLASSIC)


def reverse_classic_premium(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    Package.objects.filter(slug='classic-premium').delete()
    Package.objects.filter(slug='classic').update(
        tagline='A refreshing day away with your favourite people.',
        short_description=(
            'Gather your friends or colleagues for an easy-going day away, with room to relax, '
            'reconnect and return refreshed.'
        ),
    )


class Migration(migrations.Migration):
    dependencies = [('Web', '0031_package_editorial_content')]

    operations = [
        migrations.RunPython(create_classic_premium, reverse_classic_premium),
    ]
