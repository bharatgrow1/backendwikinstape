from django.core.mail import send_mail

def send_otp_email(email, otp, is_password_reset=False):
    if is_password_reset:
        subject = 'Your OTP for Password Reset'
        message = f'Your OTP for password reset is: {otp}. This OTP is valid for 10 minutes.'
    else:
        subject = 'Your OTP for Login'
        message = f'Your OTP for login is: {otp}. This OTP is valid for 5 minutes.'
    
    send_mail(
        subject=subject,
        message=message,
        from_email='priteshbharatgrow@gmail.com',
        recipient_list=[email],
        fail_silently=False,
    )
