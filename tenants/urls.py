from django.urls import path
from . import views

urlpatterns = [
    path('explore/', views.explore, name='explore'),
    path('create/', views.tenant_create, name='tenant_create'),
    path('<int:tenant_id>/join/', views.tenant_join, name='tenant_join'),
    path('<int:tenant_id>/leave/', views.tenant_leave, name='tenant_leave'),
    path('<int:tenant_id>/chat/', views.tenant_chat_post, name='tenant_chat_post'),

    # Member Management
    path('<int:tenant_id>/members/', views.tenant_members, name='tenant_members'),
    path('<int:tenant_id>/members/<int:membership_id>/role/', views.tenant_member_role_update, name='tenant_member_role_update'),
    path('<int:tenant_id>/members/<int:membership_id>/transfer/', views.tenant_member_transfer_admin, name='tenant_member_transfer_admin'),
    path('<int:tenant_id>/members/<int:membership_id>/kick/', views.tenant_member_kick, name='tenant_member_kick'),
]
