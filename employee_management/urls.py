from django.urls import path
from . import views

urlpatterns = [
    path('', views.handle_employee_form, name='handle_employee_form'),
    path('okay', views.send_employee_emails, name='send_employee_emails'),
    
    
     
]

