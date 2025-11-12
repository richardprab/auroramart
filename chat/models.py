from django.db import models
from django.conf import settings


class ChatConversation(models.Model):
    """
    Represents a single conversation thread between a user and an admin,
    usually regarding a specific product.
    """

    MESSAGE_TYPE_CHOICES = [
        ('contact_us', 'Contact Us'),
        ('product_chat', 'Product Chat'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('replied', 'Replied'),
    ]
    
    user = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, related_name='conversations')  # Customers start chats
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='chats')
    admin = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_chats')  # Staff handle chats
    
    # NEW FIELDS
    subject = models.CharField(max_length=200, default='General Inquiry')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='contact_us')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    user_has_unread = models.BooleanField(default=False)
    admin_has_unread = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.subject}"


class ChatMessage(models.Model):
    """
    An individual message within a ChatConversation.
    """

    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    # Sender can be Customer (customer messages) or Staff (staff replies)
    sender = models.ForeignKey('accounts.Customer', on_delete=models.CASCADE, null=True, blank=True)
    # Alternative: staff_sender for staff messages (if needed)
    staff_sender = models.ForeignKey('accounts.Staff', on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']

    def __str__(self):
        sender_name = (self.sender.username if self.sender else 
                      self.staff_sender.username if self.staff_sender else 'Unknown')
        return f"{sender_name}: {self.content[:50]}"
    
    @property
    def actual_sender(self):
        """Return the actual sender (Customer or Staff)"""
        return self.staff_sender if self.staff_sender else self.sender
