from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("tables/", views.list_tables, name="tables"),
    path("data/<str:table_name>/", views.get_data, name="get_data"),
    path("analytics/<str:table_name>/", views.analytics_view, name="analytics"),
    path("analytics/<str:table_name>/daily.csv", views.daily_revenue_csv, name="daily_revenue_csv"),
    path("data-quality/<str:table_name>/", views.data_quality, name="data_quality"),
    path("ingestion-runs/", views.ingestion_runs, name="ingestion_runs"),
]
