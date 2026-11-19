from django.db import migrations, models


PACKAGE_CONTENT = {
    'classic': {
        'tagline': 'A refreshing day away with your favourite people.',
        'short_description': 'Gather your friends or colleagues for an easy-going day away, with room to relax, reconnect and return refreshed.',
        'description': "Sometimes, all you need is a change of environment and good company.\n\nClassic is designed for friends, colleagues and groups who want to step away from their everyday routines and enjoy a refreshing day together.\n\nImagine spending the day in a beautiful resort environment, enjoying the atmosphere, relaxing, sharing laughter and making memories with people you love being around.\n\nWhether you're catching up with old friends, spending quality time with colleagues or simply looking for an enjoyable day outside your usual environment, Classic gives you an opportunity to pause, recharge and reconnect.\n\nIt's more than just going out. It's giving yourself permission to enjoy life.",
        'who_is_it_for': 'Friends and friendship groups.\nColleagues and informal groups.\nPeople looking for a refreshing day out together.',
        'family_coverage': '',
    },
    'imperial': {
        'tagline': 'Stay longer. Relax deeper. Make more memories.',
        'short_description': 'A two-day, one-night group escape with time to settle in, reconnect and enjoy a longer break from the everyday.',
        'description': "Why rush back when you can stay a little longer?\n\nImperial is designed for groups who want more than a single day away. With a two-day, one-night experience, you have more time to relax, reconnect and enjoy a refreshing change of environment.\n\nTake a break from the usual demands of work and everyday responsibilities. Enjoy the pleasure of being somewhere different, sharing experiences and spending meaningful time with your group without constantly watching the clock.\n\nWhether you're travelling with friends, colleagues or a group of people who simply deserve a break, Imperial gives you the opportunity to slow down and enjoy the experience beyond a few hours.\n\nSometimes, the best memories are made when nobody is in a hurry to leave.",
        'who_is_it_for': 'Friends travelling together.\nGroups seeking an overnight resort escape.\nColleagues and organised groups looking for time away.',
        'family_coverage': '',
    },
    'paradise': {
        'tagline': 'A beautiful day. Just the two of you.',
        'short_description': 'A considered day away for two, made for slowing down, reconnecting and enjoying quality time together.',
        'description': "Sometimes, all two people need is time away from the noise of everyday life.\n\nParadise is a thoughtfully planned day escape for couples who want to relax, reconnect and enjoy each other's company in a beautiful setting.\n\nPut the routines aside. Take a break from work, responsibilities and the constant demands of daily life. Give yourselves the opportunity to enjoy a different environment, share special moments and simply be present with each other.\n\nWhether you're celebrating your relationship, marking a special occasion or just feel that you both deserve a beautiful day away, Paradise gives you the opportunity to create memories together.\n\nBecause quality time should never be left to chance.",
        'who_is_it_for': 'Married couples.\nPartners looking for quality time together.\nCouples celebrating a special occasion.\nCouples who simply want a refreshing day away.',
        'family_coverage': '',
    },
    'oasis': {
        'tagline': 'More time together. More room to reconnect.',
        'short_description': 'An overnight escape for two, giving you more time to settle in, reconnect and enjoy a change of scene.',
        'description': "Give yourselves more than a few hours together.\n\nOasis is a two-day, one-night escape designed for couples who want to slow down, reconnect and enjoy an extended break from their everyday routines.\n\nSometimes, a single day is simply not enough. Oasis gives you more time to settle into a beautiful environment, enjoy each other's company and create moments without the pressure of rushing back.\n\nWhether you're looking to celebrate your relationship, reconnect after a demanding season or simply enjoy a little time away together, Oasis offers the opportunity to make that time count.\n\nStep away from the familiar. Enjoy the moment. Make memories worth keeping.",
        'who_is_it_for': 'Married couples.\nPartners seeking an overnight getaway.\nCouples celebrating anniversaries or milestones.\nCouples who want an extended break together.',
        'family_coverage': '',
    },
    'family-break-beach-day': {
        'tagline': 'The memories they will carry long after childhood.',
        'short_description': 'A beach day for two adults and two children, created around play, fresh air and meaningful time together.',
        'description': "Childhood passes quickly, and the memories we create together matter.\n\nFamily Break Beach Day gives parents and children the opportunity to step away from their usual routines, enjoy time together and experience the simple joy of a day by the beach.\n\nLet the children enjoy the excitement of a different environment while parents get the opportunity to relax, reconnect and share in the experience.\n\nFrom the laughter and play to the beautiful family moments captured along the way, this is an opportunity to spend quality time together outside the everyday routine.\n\nThe children are growing up. Make time for the memories.\n\nA beautiful family moment to remember long after the day is over.",
        'who_is_it_for': 'Families with children.\nParents looking for quality time with their children.\nFamilies who want a refreshing beach day together.',
        'family_coverage': 'Price covers two adults and two children. Larger families can request a customised quotation.',
    },
    'oakwood': {
        'tagline': 'More than a day out. Time together that becomes a family memory.',
        'short_description': 'A two-day, one-night family getaway for two adults and two children, with time to relax, explore and reconnect.',
        'description': "Some memories deserve more than a single day.\n\nOakwood gives your family the opportunity to enjoy a longer escape, share new experiences and spend uninterrupted time together.\n\nWith a two-day, one-night experience, there is more room to relax, explore your surroundings and enjoy being together without the rush of returning home after just a few hours.\n\nFrom the excitement of arriving somewhere new to the pleasure of sharing meals, relaxing and enjoying the resort environment, Oakwood creates an opportunity for families to reconnect and make beautiful memories.\n\nThe children are growing. Life is moving. Give yourselves the gift of time together.\n\nBecause some of the most valuable things we give our children are the memories we create with them.",
        'who_is_it_for': 'Families with children.\nParents who want an overnight family getaway.\nFamilies looking to create special memories together.',
        'family_coverage': 'Price covers two adults and two children. Larger families can request a customised quotation.',
    },
}


def update_launch_packages(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    launch_price = {
        'classic': '50000',
        'imperial': '150000',
        'paradise': '120000',
        'oasis': '200000',
        'family-break-beach-day': '180000',
        'oakwood': '400000',
    }
    for slug, content in PACKAGE_CONTENT.items():
        Package.objects.filter(slug=slug).update(
            **content, price_per_person=launch_price[slug],
        )


def reverse_content(apps, schema_editor):
    Package = apps.get_model('Web', 'GroupGetawayPackage')
    Package.objects.filter(slug__in=PACKAGE_CONTENT).update(
        tagline='', who_is_it_for='', family_coverage='',
    )


class Migration(migrations.Migration):
    dependencies = [('Web', '0030_post_design_template_alter_post_author')]

    operations = [
        migrations.AddField(
            model_name='groupgetawaypackage', name='tagline',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='who_is_it_for',
            field=models.TextField(blank=True, help_text='One audience description per line'),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='family_coverage',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='groupgetawaypackage', name='card_image',
            field=models.ImageField(blank=True, null=True, upload_to='packages/cards/'),
        ),
        migrations.RunPython(update_launch_packages, reverse_content),
    ]
