from rest_framework import serializers
from .models import Announcement, Category, Village, Banner, Photo, Favorite, PendingAnnouncement, PendingAnnouncementPhoto, PendingAnnouncementEdit, PendingPhoto

class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image']

class CategorySerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = '__all__'
    
    def get_photo(self, obj):
        if obj.photo:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return ''

class AnnouncementSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)

    class Meta:
        model = Announcement
        fields = '__all__'

class VillageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Village
        fields = '__all__'

class BannerSerializer(serializers.ModelSerializer):
    announcement_name = serializers.CharField(source='announcement.name', read_only=True)

    class Meta:
        model = Banner
        fields = '__all__'

class FavoriteSerializer(serializers.ModelSerializer):
    announcement = AnnouncementSerializer(read_only=True)
    announcement_id = serializers.PrimaryKeyRelatedField(
        queryset=Announcement.objects.all(),
        source='announcement',
        write_only=True
    )

    class Meta:
        model = Favorite
        fields = ['id', 'device_token', 'announcement', 'announcement_id']

class PendingAnnouncementPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingAnnouncementPhoto
        fields = ['id', 'image']

class PendingAnnouncementSerializer(serializers.ModelSerializer):
    pending_photos = PendingAnnouncementPhotoSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PendingAnnouncement
        fields = '__all__'

class PendingPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingPhoto
        fields = ['id', 'image']

class PendingAnnouncementEditSerializer(serializers.ModelSerializer):
    pending_photos = PendingPhotoSerializer(many=True, read_only=True)
    original_announcement = AnnouncementSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    village_name = serializers.CharField(source='village.name', read_only=True)
    edited_by_username = serializers.CharField(source='edited_by.username', read_only=True)

    class Meta:
        model = PendingAnnouncementEdit
        fields = '__all__'