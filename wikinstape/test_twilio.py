# test_twilio.py
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wikinstape.settings')
django.setup()

from users.utils.twilio_service import twilio_service

def test_twilio():
    print("🔧 Testing Twilio Configuration...")
    
    # Check if client is initialized
    if not twilio_service.client:
        print("❌ Twilio client not initialized")
        return
    
    # Get service info
    service_info = twilio_service.get_service_info()
    if service_info:
        print(f"✅ Twilio Service: {service_info['friendly_name']}")
    else:
        print("❌ Could not fetch service info")
        return
    
    # Test sending OTP
    mobile = "+919170475552"  # Your verified number
    print(f"📱 Testing OTP send to: {mobile}")
    
    result = twilio_service.send_otp_sms(mobile)
    print(f"Send OTP Result: {result}")
    
    if result['success']:
        print("✅ OTP sent successfully via Twilio!")
        otp = input("Enter the OTP you received: ")
        
        # Verify OTP
        verify_result = twilio_service.verify_otp(mobile, otp)
        print(f"Verify OTP Result: {verify_result}")
        
        if verify_result['success'] and verify_result['valid']:
            print("🎉 OTP verified successfully via Twilio!")
        else:
            print("❌ OTP verification failed")
    else:
        print(f"❌ OTP send failed: {result.get('error')}")

if __name__ == "__main__":
    test_twilio()