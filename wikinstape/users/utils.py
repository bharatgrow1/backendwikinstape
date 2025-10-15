from django.core.mail import send_mail

def send_otp_email(email, otp):
    send_mail(
        subject='Your OTP for login',
        message=f'Your OTP is: {otp}',
        from_email='priteshbharatgrow@gmail.com',
        recipient_list=[email],
        fail_silently=False,
    )
