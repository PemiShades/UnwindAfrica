from decimal import Decimal

from django.db import migrations, models


URS_BENEFITS = (
    'A year of relaxation and wellness, with flexible quarterly payment options. '
    'Plans can include massages, mani-pedi sessions, boat cruises, exclusive events, '
    'counselling and therapy sessions, birthday celebrations and weekend getaways. '
    'The experience is designed to make more room for family, friends and lasting memories.'
)


PACKAGES = [
    # URS solo collection
    ('Sunflower', 'urs', 'solo', 'Brighten your day with a rejuvenating solo escape.', 'A flower-inspired solo experience for self-care, relaxation and a little time to recharge.'),
    ('Daisy', 'urs', 'solo', 'Find peace and tranquillity in a serene setting.', 'A gentle solo escape designed to give you space to slow down and reset.'),
    ('Lily', 'urs', 'solo', 'Luxury self-care, thoughtfully tailored to you.', 'A more indulgent solo wellness experience shaped around your needs.'),
    ('Rose', 'urs', 'solo', 'A rejuvenating escape centred on self-love.', 'Take time for yourself with a restorative escape designed to help you unwind and recharge.'),
    ('Orchid', 'urs', 'solo', 'Ultimate relaxation in an exclusive setting.', 'A flower-inspired solo experience for those seeking an elevated level of comfort and calm.'),
    # URS couples collection
    ('Romantic Escapes', 'urs', 'couples', 'For proposals, anniversaries and rekindling love.', 'Create a moment together with a romantic experience that can be customised to your story.'),
    ('Relaxation Retreats', 'urs', 'couples', 'Unwind and rejuvenate together.', 'A shared retreat with room to slow down, reconnect and enjoy a serene setting.'),
    ('Luxury Getaways', 'urs', 'couples', 'A more indulgent escape, made for two.', 'A customisable couples experience with a focus on comfort, romance and time together.'),
    # URS family collection
    ('Family Wellness Escape', 'urs', 'family', 'Bring the family together for time to rest and reconnect.', 'A customisable family experience in a serene setting, with memorable moments shaped around your interests.'),
    # Additional experiences
    ('Corporate Retreats', 'corporate', '', 'Recharge, refocus and rebuild your team.', 'A customised corporate retreat with team-building activities, strategic planning, workshops, relaxation and time to bond. Designed around your organisation’s needs.'),
    ('Coastal Breeze', 'boat', '', 'An intimate cruise for small groups or families.', 'Set sail for a peaceful escape, a celebration or time together on the water. Contact us to shape the cruise around your occasion.'),
    ('Ocean Oasis', 'boat', '', 'Take in the ocean views with snacks and drinks.', 'A relaxed cruise experience with ocean views, snacks and drinks for a delightful time on the water.'),
    ('Sea Haven', 'boat', '', 'A spacious, comfortable cruise for a larger group.', 'Gather friends and family for a roomy cruise experience with time to celebrate and enjoy the water.'),
    ('Luxury Voyager', 'boat', '', 'A premium cruise with elevated amenities and service.', 'A more indulgent boat experience for romance, celebrations or an unhurried ocean escape.'),
]


def seed_experiences(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    for name, category, collection_group, short, description in PACKAGES:
        inclusion = URS_BENEFITS if category == 'urs' else ''
        Package.objects.update_or_create(
            slug=name.lower().replace(' ', '-'),
            defaults={
                'name': name,
                'category': category,
                'collection_group': collection_group,
                'quote_only': True,
                'experience_duration': 'annual' if category == 'urs' else ('custom' if category in {'boat', 'corporate'} else 'one_day'),
                'pricing_basis': 'person',
                'included_adults': 1,
                'included_children': 0,
                'price_per_person': Decimal('0.00'),
                'tagline': short,
                'short_description': short,
                'description': description + ('\n\n' + URS_BENEFITS if category == 'urs' else ''),
                'inclusions': inclusion,
                'is_active': True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [('Web', '0032_classic_premium_group_getaway')]

    operations = [
        migrations.AddField(
            model_name='groupgetawaypackage',
            name='collection_group',
            field=models.CharField(blank=True, choices=[('solo', 'Solo Packages'), ('couples', 'Couples Packages'), ('family', 'Family Packages')], db_index=True, max_length=20),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage',
            name='quote_only',
            field=models.BooleanField(default=False, help_text='Show enquiry details instead of checkout until a price is configured.'),
        ),
        migrations.AlterField(
            model_name='groupgetawaypackage',
            name='category',
            field=models.CharField(choices=[('group', 'Group Getaway'), ('couples', 'Couples Escape'), ('family', 'Family Moments'), ('urs', 'Unwind Relaxation Services'), ('corporate', 'Corporate Retreats'), ('boat', 'Boat Cruise Specials')], db_index=True, default='group', max_length=20),
        ),
        migrations.AlterField(
            model_name='groupgetawaypackage',
            name='experience_duration',
            field=models.CharField(choices=[('one_day', 'One Day'), ('two_days_one_night', 'Two Days, One Night'), ('annual', 'Annual Plan'), ('custom', 'Arranged to Suit')], db_index=True, default='one_day', max_length=30),
        ),
        migrations.RunPython(seed_experiences, migrations.RunPython.noop),
    ]
