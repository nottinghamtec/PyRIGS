# endpoint                            method          result
#
# api/assets/                         get             list all assets
# api/assets/<id>                     get             get a specific asset


from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from django.db.models import Min
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.template import Context, RequestContext
import datetime

from assets import models
from django.conf import settings


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Asset
        fields = '__all__'


class AssetViewSet(viewsets.ModelViewSet):
    queryset = models.Asset.objects.all()
    serializer_class = AssetSerializer
