from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_payment_confirmation_email(user_email, booking_id):
    send_mail(
        subject="Booking Payment Confirmed",
        message=f"Your booking {booking_id} has been successfully paid.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email]
    )
    
    return f"Payment confirmation email sent to {user_email} for booking {booking_id}"

@shared_task
def send_booking_confirmation_email(user_email, booking_id):
    """
    Celery task to send a booking confirmation email.
    """
    subject = "Booking Confirmation"
    message = f"Dear customer, Your booking (ID: {booking_id}) has been confirmed. Thank you for choosing us!"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user_email]

    send_mail(subject, message, from_email, recipient_list)

    return f"Booking confirmation email sent to {user_email} for booking {booking_id}"