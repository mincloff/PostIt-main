# pyrefly: ignore [missing-import]
from django.shortcuts import render
# pyrefly: ignore [missing-import]
from django.http import HttpResponse

def policy(request):
    return render(request, 'policy.html')

def tos(request):
    return render(request, 'tos.html')

def tiktok(request):
    return render(request, 'tiktokmhtTXhUjYfG3YODPQSXSgUpTKL7XQoIj.txt')

def ping(request):
    return HttpResponse("pong")