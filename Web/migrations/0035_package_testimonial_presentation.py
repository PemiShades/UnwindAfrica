from django.db import migrations, models

EXCERPTS = {'Blessing Okiri': "I had been overwhelmed by responsibilities. Hearing other women's stories reminded me that I am not alone in life's struggles. Rest felt like a valuable gift, and I left feeling emotionally relaxed and renewed.", 'Ebunoluwa Oke': "Between work, home and personal responsibilities, I was constantly multitasking. Hearing other women's stories and having time without thinking about the kids or work reminded me how important rest and balance are. I left motivated to intentionally make room for rest.", 'Olubunmi Akogun': 'Life had felt heavy and exhausting. Sharing stories with other women created a priceless bond. Watching the waves and feeling the breeze felt therapeutic. Rest felt like freedom, a new beginning, a new strength and a new me.', 'Abosede Ajayi Kannike': "I was tired, stretched thin and carrying everyone's weight but my own. At the beach, I could simply be present, with no pressure to perform. Rest felt like breathing again. I left feeling refreshed, seen and peaceful.", 'Amos Oladoye Oladimeji': 'I hardly had time to rest before the experience. I especially enjoyed the chit-chat and medical check-up, and connecting with like-minded people. It made me feel really good and was highly emotional for me. I look forward to experiencing it again.', 'Jolly Igiebor': "Sometimes, life feels like it's about others and not for me. I appreciated meeting other men, learning from their experiences and seeing life from different angles. I felt blessed. It reminded me that no matter how grown you are, there is room for fun.", 'Akinlolu Odubitan': 'I felt listless before the experience. Meeting other men and just being free meant a lot. Hearing their insights and different perspectives on life was awe-inspiring. I left excited and humble, reminded that no matter how grown you are, there is room for fun.', 'Adereti Best': 'I felt choked before the experience. The health check and unscripted interactions stood out, and I felt relaxed and at ease. My message to anyone constantly working and carrying responsibilities is simple: when you die, life will still continue. REST.'}

def populate_excerpts(apps, schema_editor):
    Story = apps.get_model('Web', 'UnwinderStory')
    for name, excerpt in EXCERPTS.items():
        Story.objects.filter(name=name, package_excerpt='').update(package_excerpt=excerpt)

class Migration(migrations.Migration):
    dependencies = [('Web', '0034_unwinder_stories')]
    operations = [
        migrations.AddField(model_name='unwinderstory', name='package_excerpt', field=models.TextField(blank=True, help_text='Short first-person version for the package page. The original story is retained.')),
        migrations.AddField(model_name='unwinderstory', name='experience_date', field=models.DateField(blank=True, null=True, help_text="Date of the participant's experience. Only month and year are displayed.")),
        migrations.RunPython(populate_excerpts, migrations.RunPython.noop),
    ]
