from django.urls import path
from vendorpayment.views import download_vendor_receipt, view_vendor_receipt

urlpatterns = [
    path('receipt/download/<int:payment_id>/', download_vendor_receipt, name='download_vendor_receipt'),
    path('receipt/view/<int:payment_id>/', view_vendor_receipt, name='view_vendor_receipt')
]