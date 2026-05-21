# pyrefly: ignore [missing-import]
from django.http import HttpResponse
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
from core.models import PlatformIntegration, Organization

def home(request):
    return render(request, 'home.html')

@login_required
def manage(request):
    # Fetch all integrations for the user's primary organization (assuming one-to-one for now)
    # or just fetch all integrations if the user is owner.
    # We will pass them generically.
    integrations = PlatformIntegration.objects.filter(organization__owner=request.user)

    context = {
        'integrations': integrations,
    }
    return render(request, 'manage.html', context)

def policy(request):
    return render(request, 'policy.html')

def tos(request):
    return render(request, 'tos.html')

@login_required
def compose(request):
    integrations = PlatformIntegration.objects.filter(organization__owner=request.user)

    context = {
        'integrations': integrations,
    }
    return render(request, 'compose.html', context)

def tiktok_verification(request):
    return HttpResponse("tiktok-developers-site-verification=mhtTXhUjYfG3YODPQSXSgUpTKL7XQoIj", content_type="text/plain")

def ping(request):
    """Health check endpoint to keep Render free tier alive"""
    # pyrefly: ignore [missing-import]
    from django.http import JsonResponse
    return JsonResponse({"status": "ok", "message": "pong"})
