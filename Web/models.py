# Create your models here.
from django.db import models


def upload_thumbnail_image(self, post_id):
	return "uploads/posts/{post_id}"

# blog model
class Post(models.Model):
	thumbnail = models.ImageField(upload_to='')
	category = models.CharField(max_length=50, choices=[('luxury','Luxury'),('welnspa','Welness and Spa')],  default='luxury', help_text='select category',null=True, blank=True)
	title = models.CharField(max_length=350)
	content = models.TextField(null=True,help_text="Write here")