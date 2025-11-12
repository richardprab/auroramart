from django.db import models
from django.contrib.auth import get_user_model # IMPORTED AS REQUESTED

User = get_user_model() # USED AS REQUESTED

class HomepageBanner(models.Model):
    """
    Model for admin-controlled homepage banners, pop-ups,
    or promotional content.
    """
    title = models.CharField(max_length=255)
    message = models.TextField(help_text="The main content of the banner/pop-up.")
    link = models.URLField(
        max_length=1024,
        null=True,
        blank=True,
        help_text="An optional URL to link to (e.g., /sale/summer-sale)."
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Only active banners will be shown on the site."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

