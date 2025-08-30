# ALX Travel App

This Django project implements a travel booking system with payment integration using Chapa's sandbox environment. It allows users to create bookings, initiate payments, and verify payment statuses.

## Features

- User authentication (custom user model `listings.User`).
- Booking creation and management.
- Payment initiation and verification via Chapa API.
- RESTful API endpoints for listings, bookings, and payments.
- CORS enabled for all origins.
- Email confirmation for payments (console backend in development).

## Setup Instructions

1. Clone the repository:

```bash
git clone <repository_url>
cd alx_travel_app_0x02
```

2. Create a `.env` file with the following variables:

```env
SECRET_KEY=<your_django_secret>
DEBUG=True
DB_NAME=<your_db_name>
DB_USER=<your_db_user>
DB_PASSWORD=<your_db_password>
CHAPA_SECRET_KEY=<your_chapa_secret_key>
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Apply migrations:

```bash
python manage.py migrate
```

5. Create a superuser (optional for admin access):

```bash
python manage.py createsuperuser
```

6. Run the development server:

```bash
python manage.py runserver
```

## API Endpoints

### Bookings

- **Create booking**

  - `POST /api/bookings/`
  - Body:
    ```json
    {
      "listing": "<listing_id>",
      "guest": "<user_id>",
      "check_in": "2025-08-17",
      "check_out": "2025-08-18"
    }
    ```

- **List bookings**

  - `GET /api/bookings/`

### Payments

- **Initiate payment**

  - `POST /api/payments/`
  - Body:
    ```json
    {
      "booking": "<booking_id>",
      "amount": "1600.00"
    }
    ```
  - Response includes `checkout_url` for Chapa sandbox payment.

- **Verify payment**

  - `GET /api/payments/<payment_id>/verify/`
  - Verifies payment status using Chapa API and updates `payment_status` in the database.

## Chapa Payment Integration

1. Payments are initiated via Chapa sandbox using `CHAPA_SECRET_KEY`.
2. Transaction ID (`tx_ref`) is generated for each payment.
3. Verification process fetches the payment details from Chapa:

```json
{
  "message": "Payment details fetched successfully",
  "status": "success",
  "data": {
    "amount": 1600,
    "status": "success",
    "tx_ref": "<tx_ref>",
    ...
  }
}
```

4. On successful verification, `payment_status` in the database is updated to `completed`.

## Testing

- Payment flow tested using Postman and Chapa sandbox.
- Example request in Postman for initiating payment:

```json
{
  "booking": "962dcc10-9305-4c32-85b4-a66819cb2034",
  "amount": "1600.00"
}
```

- Chapa sandbox receipt verified, payment marked as `completed` in the system.

## Notes

- Ensure Celery is running if using asynchronous tasks for sending emails.
- Payment integration uses Chapa sandbox; replace with live keys in production.
- Email backend is set to console for development; configure SMTP for production.

---

This README provides a full overview of the project setup, API usage, and tests performed during development.