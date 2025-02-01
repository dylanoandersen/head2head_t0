from django.core.paginator import Paginator
from django.shortcuts import render
from django.http import JsonResponse
from .models import Player
from .serializers import PlayerInfoSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import PageNumberPagination

# Create your views here.

@api_view(['GET'])
def allPlayer(request):
    paginator = PageNumberPagination()
    paginator.page_size = 50
    player = Player.objects.all()
    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player, many=True)
        return Response({"Player": serializer.data})
    else:
        print('Could not grab all players')

@api_view(['GET'])
def player_info(request,id):
    try:
        player = Player.objects.get(pk=id)
    except Player.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerInfoSerializer(player)
        return Response({"Player": serializer.data})


