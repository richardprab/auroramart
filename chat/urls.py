from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    # AJAX endpoints (JSON responses)
    path("ajax/conversations/", views.list_conversations, name="ajax_list_conversations"),
    path("ajax/conversations/create/", views.create_conversation, name="ajax_create_conversation"),
    path("ajax/conversations/<int:conversation_id>/", views.get_conversation, name="ajax_get_conversation"),
    path("ajax/conversations/<int:conversation_id>/send/", views.send_message, name="ajax_send_message"),
    path("ajax/conversations/<int:conversation_id>/mark-read/", views.mark_conversation_read, name="ajax_mark_read"),
    path("ajax/conversations/<int:conversation_id>/delete/", views.delete_conversation, name="ajax_delete_conversation"),
]

