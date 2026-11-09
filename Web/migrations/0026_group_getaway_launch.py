from decimal import Decimal

from django.db import migrations, models


def seed_group_getaway(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    AddOn = apps.get_model('Web', 'PackageAddOn')

    packages = [
        ('Classic', 'group', 'one_day', 'person', 1, 0, 'A restorative one-day group beach experience.', '50,000'),
        ('Imperial', 'group', 'two_days_one_night', 'person', 1, 0, 'A two-day, one-night group escape.', '150,000'),
        ('Paradise', 'couples', 'one_day', 'couple', 2, 0, 'A considered one-day escape for two.', '120,000'),
        ('Oasis', 'couples', 'two_days_one_night', 'couple', 2, 0, 'A two-day, one-night escape for two.', '200,000'),
        ('Family Break Beach Day', 'family', 'one_day', 'family', 2, 2, 'A family beach day starting price for two adults and two children.', '180,000'),
        ('Oakwood', 'family', 'two_days_one_night', 'family', 2, 2, 'A two-day, one-night family stay starting price for two adults and two children.', '400,000'),
    ]

    Package.objects.all().update(is_active=False)
    for name, category, duration, basis, adults, children, description, price in packages:
        Package.objects.update_or_create(
            slug=name.lower().replace(' ', '-'),
            defaults={
                'name': name,
                'category': category,
                'experience_duration': duration,
                'pricing_basis': basis,
                'included_adults': adults,
                'included_children': children,
                'price_per_person': Decimal(price.replace(',', '')),
                'short_description': description,
                'description': description,
                'inclusions': '',
                'flyer': '',
                'is_active': True,
                'instalment_charge_percent': Decimal('0'),
                'instalment_charge_flat': Decimal('0'),
                'available_durations': '3,6,9,12',
            },
        )

    AddOn.objects.filter(name__icontains='doctor').update(price=Decimal('35000'), is_active=True)
    AddOn.objects.update_or_create(
        name='Transportation',
        defaults={
            'description': 'Optional transport, from ₦20,000 per person. Final pricing depends on pickup location and arrangement.',
            'price': Decimal('20000'),
            'regular_price': Decimal('20000'),
            'is_active': True,
        },
    )
    AddOn.objects.update_or_create(
        name='My Doctor & I',
        defaults={
            'description': 'Optional wellness experience.',
            'price': Decimal('35000'),
            'regular_price': Decimal('35000'),
            'is_active': True,
        },
    )


def unseed_group_getaway(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    Package.objects.filter(name__in=[
        'Classic', 'Imperial', 'Paradise', 'Oasis',
        'Family Break Beach Day', 'Oakwood',
    ]).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('Web', '0025_packagepayment_paystack_reference_and_more')]

    operations = [
        migrations.AddField(
            model_name='groupgetawaypackage', name='category',
            field=models.CharField(choices=[('group', 'Group Getaway'), ('couples', 'Couples Escape'), ('family', 'Family Moments')], db_index=True, default='group', max_length=20),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='experience_duration',
            field=models.CharField(choices=[('one_day', 'One Day'), ('two_days_one_night', 'Two Days, One Night')], db_index=True, default='one_day', max_length=30),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='pricing_basis',
            field=models.CharField(choices=[('person', 'Per person'), ('couple', 'Per couple'), ('family', 'Per family (2 adults, 2 children)')], default='person', max_length=20),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='included_adults',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='included_children',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='packageorder', name='party_size',
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='packageorder', name='transportation_selected',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='packageorder', name='transportation_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='packageorder', name='transportation_pickup_location',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='packageorder', name='early_access_discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='packageorder', name='early_access_slot',
            field=models.PositiveSmallIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='packageorder', name='early_access_confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='packageorder', name='overpayment_credit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='packagepayment', name='is_initial_deposit',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='packagepayment', name='authorization_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='packagepayment', name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('success', 'Successful'), ('failed', 'Failed')], db_index=True, default='success', max_length=20),
        ),
        migrations.AddField(
            model_name='packagepayment', name='paystack_response',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='GroupGetawayEarlyAccessOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='group-getaway-launch', max_length=80, unique=True)),
                ('capacity', models.PositiveSmallIntegerField(default=20)),
                ('confirmed_count', models.PositiveSmallIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='PackageCustomerCredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password_hash', models.CharField(max_length=128)),
                ('password_sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RunPython(seed_group_getaway, unseed_group_getaway),
        migrations.RunPython(
            lambda apps, schema_editor: apps.get_model('Web', 'GroupGetawayEarlyAccessOffer').objects.get_or_create(pk=1),
            migrations.RunPython.noop,
        ),
    ]
