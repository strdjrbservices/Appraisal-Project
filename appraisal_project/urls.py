from django.urls import path
from extractor import views

urlpatterns = [
    path('', views.upload_pdf, name='upload_pdf'),
    path('extract/<str:filename>/<str:section_name>/', views.extract_section, name='extract_section'),
    path('compare/', views.compare_pdfs_view, name='compare_pdfs'),
    path('compare-html-pdf/', views.compare_html_pdf_view, name='compare_html_pdf'),
]