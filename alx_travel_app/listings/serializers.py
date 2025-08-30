from rest_framework import serializers
from .models import Listing, Booking, User, Review, Payment
from rest_framework.authtoken.serializers import AuthTokenSerializer

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['user_id', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'password', 'created_at']
        read_only_fields = ['user_id', 'created_at']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.full_clean()  # runs model.clean()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.full_clean()
        instance.save()
        return instance

class ListingSerializer(serializers.ModelSerializer):
    host = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Listing
        fields = ['listing_id', 'host', 'title', 'description', 'location',
                  'price_per_night', 'max_guests', 'is_available',
                  'created_at', 'updated_at']
        read_only_fields = ('listing_id', 'created_at', 'updated_at')

    def create(self, validated_data):
        # assume view sets host via serializer.save(host=self.request.user)
        listing = Listing(**validated_data)
        listing.full_clean()
        listing.save()
        return listing

class BookingSerializer(serializers.ModelSerializer):
    guest = serializers.PrimaryKeyRelatedField(read_only=True)
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())
    checkout_url = serializers.SerializerMethodField(read_only=True)  # new field

    class Meta:
        model = Booking
        fields = [
            'booking_id', 'guest', 'listing', 'check_in_date',
            'check_out_date', 'num_guests', 'total_price',
            'booking_status', 'created_at', 'checkout_url'  # added field
        ]
        read_only_fields = ('booking_id', 'created_at', 'booking_status', 'checkout_url')

    def get_checkout_url(self, obj):
        # Return the dynamically attached checkout_url from BookingViewSet.perform_create
        return getattr(obj, 'checkout_url', None)

    def validate(self, data):
        if data.get('check_in_date') and data.get('check_out_date'):
            if data['check_in_date'] >= data['check_out_date']:
                raise serializers.ValidationError({'check_out_date': 'Check-out must be after check-in.'})
        if data.get('num_guests') is not None and data.get('listing'):
            if data['num_guests'] > data['listing'].max_guests:
                raise serializers.ValidationError({'num_guests': 'Number of guests exceeds listing capacity.'})
            if data['num_guests'] < 1:
                raise serializers.ValidationError({'num_guests': 'Must book for at least 1 guest.'})
        return data


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.all())

    class Meta:
        model = Review
        fields = ['review_id', 'booking', 'listing', 'reviewer',
                  'rating', 'comment', 'created_at']
        read_only_fields = ('review_id', 'created_at')

    def validate(self, data):
        booking = data.get('booking')
        listing = data.get('listing')
        # reviewer is set in view from request.user; can't check here unless context provided
        if booking and listing and listing != booking.listing:
            raise serializers.ValidationError("Listing must match the booking's listing.")
        return data

    def create(self, validated_data):
        review = Review(**validated_data)
        review.full_clean()
        review.save()
        return review


class CustomAuthTokenSerializer(AuthTokenSerializer):
    email = serializers.EmailField(label="Email", write_only=True)
    username = None  # remove username field

    def validate(self, attrs):
        # Use email instead of username for authentication
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Authenticate with email and password
            from django.contrib.auth import authenticate
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("Unable to log in with provided credentials.", code='authorization')
        else:
            raise serializers.ValidationError("Must include email and password.", code='authorization')

        attrs['user'] = user
        return attrs
    
class PaymentSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    checkout_url = serializers.SerializerMethodField(read_only=True)  # new field

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'booking', 'transaction_id', 'payment_status',
            'amount', 'created_at', 'checkout_url'
        ]
        read_only_fields = ('payment_id', 'created_at', 'payment_status', 'checkout_url')

    def get_checkout_url(self, obj):
        # Return checkout_url if it exists (attached during creation)
        return getattr(obj.booking, 'checkout_url', None)

    def validate(self, data):
        booking = data.get('booking')
        amount = data.get('amount')

        if booking and not booking.listing.is_available:
            raise serializers.ValidationError({'booking': 'Cannot pay for an unavailable listing.'})

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({'amount': 'Payment amount must be greater than zero.'})

        return data

    def create(self, validated_data):
        payment = Payment(**validated_data)
        payment.full_clean()
        payment.save()
        return payment

    def update(self, instance, validated_data):
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.full_clean()
        instance.save()
        return instance