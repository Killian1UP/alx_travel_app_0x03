import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager


class Status(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'
    
class UserRole(models.TextChoices):
    GUEST = 'guest', 'Guest'
    HOST = 'host', 'Host'
    ADMIN = 'admin', 'Admin'
    
class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'          
    COMPLETED = 'completed', 'Completed'          
    FAILED = 'failed', 'Failed'             
    CANCELLED = 'cancelled', 'Cancelled'    
    REFUNDED = 'refunded', 'Refunded'       
    
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)
    
class User(AbstractUser):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    username = None
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=10, choices=UserRole.choices, default=UserRole.GUEST)
    created_at = models.DateTimeField(auto_now_add=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = UserManager()
    
    def __str__(self):
        return self.email
    
    @property
    def is_host(self):
        return self.role == UserRole.HOST
    
    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_guest(self):
        return self.role == UserRole.GUEST
    

class Listing(models.Model):
    listing_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=150)
    description = models.TextField()
    location = models.CharField(max_length=150)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    max_guests = models.IntegerField(null=False)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        # Ensure price is not negative
        if self.price_per_night < 0:
            raise ValidationError({'price_per_night': 'Price must be zero or greater.'})
        
        # Ensure max_guests is at least 1
        if self.max_guests < 1:
            raise ValidationError({'max_guests': 'Listing must allow at least 1 guest.'})
        
    def __str__(self):
        return self.title
    
class Booking(models.Model):
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    num_guests = models.IntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING.value)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def clean(self):
        # Ensure check-in is before check-out
        if self.check_in_date >= self.check_out_date:
            raise ValidationError({'check_out_date': 'Check-out must be after check-in.'})

        # Ensure guest count does not exceed listing limit
        if self.listing and self.num_guests > self.listing.max_guests:
            raise ValidationError({'num_guests': 'Number of guests exceeds listing capacity.'})

        # Ensure at least 1 guest
        if self.num_guests < 1:
            raise ValidationError({'num_guests': 'Must book for at least 1 guest.'})
        
    def __str__(self):
        return f'Booking {self.booking_id} by {self.guest}'
        
class Review(models.Model):
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Ensure reviewer is the same as booking.guest
        if self.booking and self.reviewer != self.booking.guest:
            raise ValidationError("Reviewer must be the guest who made the booking.")

        # Ensure review is for the correct listing
        if self.booking and self.listing != self.booking.listing:
            raise ValidationError("Listing must match the one in the booking.")
        
    def __str__(self):
        return f'Review {self.review_id} ({self.rating}/5)'
    
class Payment(models.Model):
    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)  # from Chapa
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING.value)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        # Ensure amount is positive
        if self.amount <=0:
            raise ValidationError({'amount': 'Payment amount must be greater than zero.'})
        
        # Ensure amount does not exceed booking total
        if self.booking and self.amount > self.booking.total_price:
            raise ValidationError({'amount': 'Payment amount cannot exceed booking total price.'})
    
    def __str__(self):
        return f"Payment {self.transaction_id or self.payment_id} - {self.payment_status}"
