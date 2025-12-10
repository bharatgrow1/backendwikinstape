from django.urls import path
from vendorpayment.views import download_vendor_receipt, view_vendor_receipt, admin_payment_report, user_payment_summary

urlpatterns = [
    path('receipt/download/<int:payment_id>/', download_vendor_receipt, name='download_vendor_receipt'),
    path('receipt/view/<int:payment_id>/', view_vendor_receipt, name='view_vendor_receipt'),
    path('report/admin/', admin_payment_report, name='admin_payment_report'),
    path('report/user-summary/', user_payment_summary, name='user_payment_summary'),
]