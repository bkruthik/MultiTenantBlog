from django.urls import path
from . import views

urlpatterns = [
    path('report/user/<str:username>/', views.report_user, name='report_user'),
    path('report/community/<int:tenant_id>/', views.report_community, name='report_community'),
    path('reports/inbox/', views.reports_inbox, name='reports_inbox'),
    path('reports/<int:report_id>/action/', views.report_action, name='report_action'),
]
