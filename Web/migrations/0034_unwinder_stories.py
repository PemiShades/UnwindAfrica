from django.db import migrations, models


STORIES = [
    {
        'name': 'Blessing Okiri', 'headline': 'I Am Not Alone', 'package_label': 'Classic',
        'display_order': 1,
        'story': "Before the experience, I had been overwhelmed and weighed down by activities and responsibilities. What stayed with me most was the discussion. It reminded me that I am not alone in life's struggles, and that other women are also fighting and winning their battles. Rest felt like a very valuable gift. I left feeling emotionally relaxed and renewed, with a deeper appreciation for intentional moments of rest.",
    },
    {
        'name': 'Ebunoluwa Oke', 'headline': 'Rest O, Because Life No Get Duplicate', 'package_label': 'Classic Premium',
        'display_order': 2,
        'story': "Life had been truly overwhelming. Between generating leads, following up with clients, managing the home front and handling personal responsibilities, I was constantly multitasking. During the experience, hearing other women's stories and taking time away from work, business and family responsibilities made me realise how important rest and balance are. One thing I particularly appreciated was not having to think about the kids or work for a while. I left feeling motivated to intentionally make room for rest.",
    },
    {
        'name': 'Olubunmi Akogun', 'headline': 'Rest Felt Like Freedom', 'package_label': 'Imperial',
        'display_order': 3,
        'story': 'Life had felt heavy and exhausting. Even when I tried to be intentional about resting, I still carried an unsatisfying feeling of exhaustion. At Unwind Africa, sharing stories with other women and listening to them without feeling like strangers created a bond that was priceless. The beach also impacted me deeply. Watching the waves, feeling the breeze on my face and tasting the salt in the air felt therapeutic. Rest felt like freedom, a new beginning, a new strength and a new me.',
    },
    {
        'name': 'Abosede Ajayi Kannike', 'headline': 'Rest Felt Like Breathing Again', 'package_label': 'Imperial Premium',
        'display_order': 4,
        'story': 'Life felt heavy. I was constantly carrying everyone\'s weight but my own. Emotionally, I was tired, stretched thin and running on autopilot. I knew I needed rest but didn\'t know how to slow down. The beach experience gave me a moment with no schedule and no pressure to perform. I could simply be present. Rest felt like breathing again. It felt like laughter at the poolside without checking my phone, my shoulders dropping, my mind quieting and joy coming back without guilt. I left feeling refreshed, seen and peaceful.',
    },
    {
        'name': 'Amos Oladoye Oladimeji', 'headline': 'Rest Is Really Good', 'package_label': 'Solo Packages',
        'display_order': 5,
        'story': 'I hardly had time to rest and unwind before the experience. Almost all the aspects were very interesting, especially the chit-chat and the medical check-up. It was good to connect and discuss with like-minded people. The experience made me feel really good and was highly emotional for me. I look forward to experiencing it again.',
    },
    {
        'name': 'Jolly Igiebor', 'headline': 'Sometimes, Life Feels Like It\'s About Others and Not for Me', 'package_label': 'Group Getaway',
        'display_order': 6,
        'story': 'Sometimes, it feels like life is about others and not for me. During the experience, I actually rested without participating in the activity that made me rest. I appreciated getting to meet other men, learn from their experiences and see life from different angles. I felt blessed. It reminded me that no matter how grown you are, there is room for fun.',
    },
    {
        'name': 'Akinlolu Odubitan', 'headline': 'There Is Room for Fun', 'package_label': 'Group Getaway',
        'display_order': 7,
        'story': 'Before the experience, I felt listless. What I appreciated most was the opportunity to meet other men and just be free. Connecting with people I had not known before and hearing their insights was awe-inspiring. I enjoyed getting different perspectives on life. The experience left me excited and humble. It reminded me that no matter how grown you are, there is room for fun.',
    },
    {
        'name': 'Adereti Best', 'headline': 'When You Die, Life Will Still Continue. REST.', 'package_label': 'Group Getaway',
        'display_order': 8,
        'story': 'Before the experience, I felt choked. The health check and the opportunity for unscripted interactions stood out for me. The experience brought relaxation, and I felt at ease. My message to anyone constantly working and carrying responsibilities is simple: when you die, life will still continue. REST.',
    },
]


def add_stories(apps, schema_editor):
    Story = apps.get_model('Web', 'UnwinderStory')
    for data in STORIES:
        Story.objects.update_or_create(name=data['name'], defaults=data)


def remove_stories(apps, schema_editor):
    Story = apps.get_model('Web', 'UnwinderStory')
    Story.objects.filter(name__in=[story['name'] for story in STORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [('Web', '0033_expand_experience_catalogue')]

    operations = [
        migrations.CreateModel(
            name='UnwinderStory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('headline', models.CharField(max_length=200)),
                ('story', models.TextField()),
                ('package_label', models.CharField(blank=True, max_length=100)),
                ('display_order', models.PositiveSmallIntegerField(db_index=True, default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Unwinder Story',
                'verbose_name_plural': 'Unwinder Stories',
                'ordering': ['display_order', 'id'],
            },
        ),
        migrations.RunPython(add_stories, remove_stories),
    ]
