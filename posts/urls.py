from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('posts/<int:tenant_id>/', views.post_list, name='post_list'),
    path('posts/<int:tenant_id>/create/', views.post, name='post'),
    path('posts/<int:tenant_id>/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:tenant_id>/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:tenant_id>/<int:post_id>/delete/', views.post_delete, name='post_delete'),

    # Post Likes
    path('posts/<int:tenant_id>/<int:post_id>/like/', views.post_like, name='post_like'),

    # Comments & Replies
    path('posts/<int:tenant_id>/<int:post_id>/comment/', views.post_comment, name='post_comment'),
    path('posts/<int:tenant_id>/<int:post_id>/comment/<int:comment_id>/like/', views.comment_like, name='comment_like'),
    path('posts/<int:tenant_id>/<int:post_id>/comment/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),

    # Polls
    path('posts/<int:tenant_id>/<int:post_id>/poll/<int:poll_id>/vote/', views.poll_vote, name='poll_vote'),
]