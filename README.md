# ALX Travel App - Background Task Implementation

## Project Overview
This project is an enhancement of the `alx_travel_app` that introduces background task processing using Celery with RabbitMQ. The main goal was to implement an **asynchronous email notification feature** that sends booking confirmation emails when a new booking is created.

## Tasks Completed

### 1. Duplicate Project
- Duplicated the project from `alx_travel_app_0x02` to `alx_travel_app_0x03` to start with a fresh workspace for enhancements.

### 2. Configure Celery
- Installed Celery and configured it to work with **RabbitMQ** as the message broker.
- Added Celery configurations in `settings.py`.
- Created a `celery.py` file in the project root to initialize Celery with the Django project.

### 3. Define Email Task
- Created a shared task in `listings/tasks.py`:
  ```python
  from celery import shared_task
  from django.core.mail import send_mail

  @shared_task
  def send_payment_confirmation_email(email, booking_id):
      subject = f"Booking Confirmation - {booking_id}"
      message = f"Your booking with ID {booking_id} has been successfully created."
      send_mail(subject, message, 'no-reply@alx-travel.com', [email])
  ```
- The task uses the Django email backend configured in `settings.py`.

### 4. Trigger Email Task
- Modified the `BookingViewSet` in `listings/views.py` to trigger the email task asynchronously upon booking creation:
  ```python
  from .tasks import send_payment_confirmation_email

  send_payment_confirmation_email.delay(
      booking.guest.email,
      booking.booking_id
  )
  ```

### 5. Test Background Task
- Verified that the background task is triggered correctly when a new booking is created.
- Confirmed that the booking confirmation email is sent asynchronously without blocking the main application flow.

## Technologies Used
- Django REST Framework
- Celery
- RabbitMQ
- Python
- Django Email Backend

## Summary
This project successfully integrates asynchronous background task processing into the travel booking app. When a guest creates a booking, a confirmation email is sent in the background, improving user experience and application performance.

