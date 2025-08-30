import requests
from django.shortcuts import render
from .models import User, Listing, Booking, Review, Payment, PaymentStatus
from .serializers import UserSerializer, ListingSerializer, BookingSerializer, ReviewSerializer, PaymentSerializer, CustomAuthTokenSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, permissions, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from django.conf import settings
from rest_framework.decorators import action
from .tasks import send_payment_confirmation_email
import uuid

# Create your views here.

class IsAuthenticatedAndGuest(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_guest

class IsAuthenticatedAndHost(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_host

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticatedAndHost]
    
    def perform_create(self, serializer):
        serializer.save(host=self.request.user)
        
    def get_queryset(self):
        # hosts see their own listings
        return self.queryset.filter(host=self.request.user)
        
class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticatedAndGuest]

    def perform_create(self, serializer):
        booking = serializer.save(guest=self.request.user)
        amount = booking.total_price
        tx_ref = f"{booking.booking_id}-{uuid.uuid4().hex[:8]}"
        checkout_url = None

        # Try to initiate Chapa payment
        url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
        payload = {
            "amount": str(amount),
            "currency": "ETB",
            "email": self.request.user.email,
            "first_name": self.request.user.first_name,
            "last_name": self.request.user.last_name,
            "tx_ref": tx_ref,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            chapa_data = response.json()
            if response.status_code == 200 and chapa_data.get("status") == "success":
                checkout_url = chapa_data["data"]["checkout_url"]
        except requests.RequestException:
            pass

        # Always create Payment record (pending)
        payment = Payment.objects.create(
            booking=booking,
            transaction_id=tx_ref,
            amount=amount,
            payment_status=PaymentStatus.PENDING.value,
        )
        
        # Trigger async confirmation email
        send_payment_confirmation_email.delay(
            booking.guest.email,
            booking.booking_id
        )

        # Optionally attach checkout_url to booking object for frontend
        booking.checkout_url = checkout_url  # attach dynamic attribute
        return booking

        
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedAndGuest]
    
    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)
        
    def get_queryset(self):
        return Review.objects.filter(reviewer=self.request.user)
    
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticatedAndGuest]

    def get_queryset(self):
        return self.queryset.filter(booking__guest=self.request.user)

    def create(self, request, *args, **kwargs):
        booking_id = request.data.get("booking")
        amount = request.data.get("amount")

        if not booking_id or not amount:
            return Response({"error": "booking and amount are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(pk=booking_id, guest=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found or not yours"}, status=status.HTTP_404_NOT_FOUND)

        # Initialize Chapa payment
        tx_ref = f"{booking.booking_id}-{uuid.uuid4().hex[:8]}"
        url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
        payload = {
            "amount": str(amount),
            "currency": "ETB",
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "tx_ref": tx_ref,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            chapa_data = response.json()
        except requests.RequestException as e:
            return Response({"error": "Failed to connect to Chapa", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

        if response.status_code != 200 or chapa_data.get("status") != "success":
            return Response({"error": "Failed to initiate payment with Chapa", "details": chapa_data},
                            status=status.HTTP_502_BAD_GATEWAY)

        checkout_url = chapa_data["data"]["checkout_url"]

        payment = Payment.objects.create(
            booking=booking,
            transaction_id=tx_ref,
            amount=amount,
            payment_status=PaymentStatus.PENDING.value,
        )

        serializer = self.get_serializer(payment)
        return Response({
            "payment": serializer.data,
            "checkout_url": checkout_url
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='verify')
    def verify_payment(self, request, pk=None):
        """Verify payment status with Chapa and update Payment"""
        try:
            payment = Payment.objects.get(pk=pk, booking__guest=request.user)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found or not yours"}, status=status.HTTP_404_NOT_FOUND)

        url = f"https://api.chapa.co/v1/transaction/verify/{payment.transaction_id}"
        headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
            chapa_data = response.json()
        except requests.RequestException as e:
            return Response({"error": "Failed to connect to Chapa", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

        if response.status_code == 200 and chapa_data.get("status") == "success":
            status_str = chapa_data["data"]["status"].lower()
            if status_str == "success":
                payment.payment_status = PaymentStatus.COMPLETED.value
                payment.save()
                # Trigger confirmation email asynchronously
                send_payment_confirmation_email.delay(payment.booking.guest.email, payment.booking.booking_id)
            elif status_str == "failed":
                payment.payment_status = PaymentStatus.FAILED.value
                payment.save()
            else:
                payment.payment_status = PaymentStatus.PENDING.value
                payment.save()
        else:
            return Response({"error": "Chapa verification failed", "details": chapa_data},
                            status=status.HTTP_502_BAD_GATEWAY)

        serializer = self.get_serializer(payment)
        return Response(serializer.data)

class CustomObtainAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})