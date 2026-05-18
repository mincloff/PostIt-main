# pyrefly: ignore [missing-import]
from django.http import HttpResponse
# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect
from youtube.models import YouTubeAccount
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from meta.models import MetaAccount
# pyrefly: ignore [missing-import]
from x.models import XAccount
# pyrefly: ignore [missing-import]
from tiktok.models import TikTokAccount
# pyrefly: ignore [missing-import]
from linkedin.models import LinkedInAccount
# pyrefly: ignore [missing-import]
from threads.models import ThreadsAccount

def home(request):
    return render(request, 'home.html')

@login_required
def manage(request):
    meta_acc = MetaAccount.objects.filter(user=request.user)
    yt_acc = YouTubeAccount.objects.filter(user=request.user)
    x_acc = XAccount.objects.filter(user=request.user)
    tiktok_acc = TikTokAccount.objects.filter(user=request.user)
    linkedin_acc = LinkedInAccount.objects.filter(user=request.user)
    thread_acc = ThreadsAccount.objects.filter(user=request.user)

    context = {
        'yt_acc': yt_acc,
        'meta_acc': meta_acc,
        'x_acc': x_acc,
        'tiktok_acc': tiktok_acc,
        'linkedin_acc': linkedin_acc,
        'thread_acc': thread_acc,
    }
    return render(request, 'manage.html', context)

def policy(request):
    return render(request, 'policy.html')

def tos(request):
    return render(request, 'tos.html')

@login_required
def compose(request):
    meta_acc = MetaAccount.objects.filter(user=request.user)
    yt_acc = YouTubeAccount.objects.filter(user=request.user)
    x_acc = XAccount.objects.filter(user=request.user)
    tiktok_acc = TikTokAccount.objects.filter(user=request.user)
    linkedin_acc = LinkedInAccount.objects.filter(user=request.user)
    thread_acc = ThreadsAccount.objects.filter(user=request.user)

    context = {
        'yt_acc': yt_acc,
        'meta_acc': meta_acc,
        'x_acc': x_acc,
        'tiktok_acc': tiktok_acc,
        'linkedin_acc': linkedin_acc,
        'thread_acc': thread_acc,
    }
    return render(request, 'compose.html', context)


def tiktok_verification(request):
    return HttpResponse("tiktok-developers-site-verification=mhtTXhUjYfG3YODPQSXSgUpTKL7XQoIj", content_type="text/plain")

def ping(request):
    """Health check endpoint to keep Render free tier alive"""
    # pyrefly: ignore [missing-import]
    from django.http import JsonResponse
    return JsonResponse({"status": "ok", "message": "pong"})
