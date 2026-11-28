from rest_framework import serializers
from store.models import Product, Category
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class ProductSerializer(serializers.ModelSerializer):

    category_name = serializers.StringRelatedField(
        source='category',
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'category',
            'category_name',
            'image',
            'available',
            'created_at',
        ]

        read_only_fields = fields


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'slug',
        ]

        read_only_fields = fields

class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)