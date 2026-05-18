# pyrefly: ignore [missing-import]
from django.contrib.auth import login, logout, authenticate
# pyrefly: ignore [missing-import]
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# pyrefly: ignore [missing-import]
from django.shortcuts import render
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.shortcuts import redirect, get_object_or_404
from .models import TransactionLog, SocialPost, PlatformIntegration 
import markdown
import requests


import os
# pyrefly: ignore [missing-import]
import google.generativeai as genai


@login_required
def dashboard(request):
    balance = 0
    org_name = "No Organization Linked"
    
    # Check if the logged-in user owns an organization
    if request.user.owned_organizations.exists():
        org = request.user.owned_organizations.first()
        org_name = org.name
        
        # Check if that organization has a wallet
        if hasattr(org, 'wallet'):
            balance = org.wallet.balance
            
    context = {
        'username': request.user.username,
        'org_name': org_name,
        'balance': balance
    }
    
    return render(request, 'core/dashboard.html', context)



# Define your SaaS Pricing Model globally
TOKENS_PER_RUPEE = 100 

@login_required
def generate_post(request):
    if request.method == 'POST':
        org = request.user.owned_organizations.first()
        if not org or not hasattr(org, 'wallet'):
            return redirect('dashboard')
            
        wallet = org.wallet
        user_prompt = request.POST.get('prompt', '')
        selected_style = request.POST.get('style', 'a short, punchy social media update')
        selected_tone = request.POST.get('tone', 'casual and friendly')
        platforms_list = request.POST.getlist('platforms')
        platforms_string = ", ".join(platforms_list) if platforms_list else "None"

        # Pre-flight check: Ensure they have at least 500 tokens (approx 1 post) to start
        if wallet.balance < 500:
            context = {
                'username': request.user.username,
                'org_name': org.name,
                'balance': wallet.balance,
                'error_message': "Insufficient tokens! Please top up your wallet."
            }
            return render(request, 'core/dashboard.html', context)

        # 1. Wake up the Gemini AI Brain
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # 1. Instruct the AI to write the post AND provide a search query
        system_instruction = f"You are an expert social media manager. Write {selected_style} that is {selected_tone} based on the following prompt. IMPORTANT: At the very bottom of your response, on a new line, write 'IMAGE_KEYWORD: ' followed by a single 1-2 word visual search term related to the post."
        full_prompt = f"{system_instruction}\n\nUser Request: {user_prompt}"
        
        # 2. Generate content
        response = model.generate_content(full_prompt)
        raw_text = response.text
        
        # 3. Parse the Keyword from the text
        generated_text = raw_text
        search_keyword = "business" # Default fallback
        
        if "IMAGE_KEYWORD:" in raw_text:
            parts = raw_text.split("IMAGE_KEYWORD:")
            generated_text = parts[0].strip() # The actual post
            search_keyword = parts[1].strip() # The keyword
            
        # 4. Translate Markdown to HTML
        html_formatted_text = markdown.markdown(generated_text)

        # --- NEW: Ping the Unsplash API ---
        # --- NEW: Ping the Unsplash API (With Loud Debugging) ---
        unsplash_url = None
        unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
        
        print(f"--- DEBUGGING IMAGE ENGINE ---")
        print(f"Keyword: {search_keyword}")
        print(f"Key Loaded: {bool(unsplash_key)}")
        
        if unsplash_key:
            try:
                unsplash_api = f"https://api.unsplash.com/photos/random?query={search_keyword}&orientation=landscape&client_id={unsplash_key}"
                img_response = requests.get(unsplash_api)
                
                print(f"Unsplash Status Code: {img_response.status_code}")
                
                if img_response.status_code == 200:
                    unsplash_url = img_response.json()['urls']['regular']
                    print("SUCCESS: Image URL acquired!")
                else:
                    print(f"UNSPLASH ERROR RESPONSE: {img_response.text}")
            except Exception as e:
                print(f"PYTHON REQUEST ERROR: {e}")
        print(f"------------------------------")

        # 5. Calculate Tokens
        total_characters = len(user_prompt) + len(raw_text)
        exact_tokens_used = max(1, total_characters // 4)

        # 6. Deduct and Log
        if wallet.deduct_tokens(exact_tokens_used):
            TransactionLog.objects.create(
                wallet=wallet, action_type="GEMINI_API_CALL", tokens_deducted=exact_tokens_used, status="SUCCESS"
            )
            
            # Save Post WITH Image URL
            SocialPost.objects.create(
                organization=org, original_prompt=user_prompt, generated_text=html_formatted_text, 
                target_platforms=platforms_string, image_url=unsplash_url
            )
            
            context = {
                'username': request.user.username,
                'org_name': org.name,
                'balance': wallet.balance,
                'generated_text': html_formatted_text,
                'generated_image': unsplash_url, # <-- Pass image to template
                'success_message': f"Used {exact_tokens_used} tokens. Prepared for: {platforms_string}" 
            }
            return render(request, 'core/dashboard.html', context)

    return redirect('dashboard')

    return redirect('dashboard')

@login_required
def store(request):
    org = request.user.owned_organizations.first()
    # Pass the current balance so they know how much they have
    context = {
        'balance': org.wallet.balance if org and hasattr(org, 'wallet') else 0
    }
    return render(request, 'core/store.html', context)

@login_required
def checkout(request):
    if request.method == 'POST':
        org = request.user.owned_organizations.first()
        if not org or not hasattr(org, 'wallet'):
            return redirect('store')
            
        wallet = org.wallet
        package = request.POST.get('package')
        
        # Our SaaS Pricing Model (1 PKR = 100 Tokens)
        packages = {
            'basic': {'pkr': 500, 'tokens': 50000},
            'pro': {'pkr': 1000, 'tokens': 100000},
            'ultra': {'pkr': 5000, 'tokens': 500000},
        }
        
        if package in packages:
            # 1. Add the tokens to the vault
            tokens_to_add = packages[package]['tokens']
            wallet.balance += tokens_to_add
            wallet.save()
            
            # 2. Log the receipt
            TransactionLog.objects.create(
                wallet=wallet,
                action_type=f"TOP_UP_{package.upper()}",
                tokens_deducted=0, # It's an addition, not a deduction
                status="SUCCESS"
            )
            
        return redirect('dashboard')
        
    return redirect('store')    
@login_required
def drafts(request):
    org = request.user.owned_organizations.first()
    posts = []
    
    if org:
        # Fetch all posts for this org, ordered by newest first ('-created_at')
        posts = SocialPost.objects.filter(organization=org).order_by('-created_at')

        for post in posts:
            post.html_text = markdown.markdown(post.generated_text)
        
    context = {
        'posts': posts,
        'org_name': org.name if org else "No Organization Linked"
    }
    
    return render(request, 'core/drafts.html', context)

def register_user(request):
    # If they are already logged in, send them to the app
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save() # <-- THIS TRIGGERS YOUR SIGNAL MAGIC!
            login(request, user) # Automatically log them in
            return redirect('dashboard')
    else:
        form = UserCreationForm()
        
    return render(request, 'core/register.html', {'form': form})

def login_user(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
        
    return render(request, 'core/login.html', {'form': form})

def logout_user(request):
    logout(request)
    return redirect('login')    

@login_required
def delete_draft(request, post_id):
    org = request.user.owned_organizations.first()
    # Security check: Find the post, but ONLY if it belongs to this org
    post = get_object_or_404(SocialPost, id=post_id, organization=org)
    
    if request.method == 'POST':
        post.delete()
        
    return redirect('drafts')

@login_required
@login_required
def edit_draft(request, post_id):
    org = request.user.owned_organizations.first()
    post = get_object_or_404(SocialPost, id=post_id, organization=org)
    
    if request.method == 'POST':
        updated_text = request.POST.get('generated_text')
        # NEW: Catch the scheduled time from the form
        scheduled_time_str = request.POST.get('scheduled_time') 
        
        if updated_text:
            post.generated_text = updated_text
            
            # NEW: Scheduling Logic
            if scheduled_time_str:
                post.scheduled_time = scheduled_time_str
                post.status = 'scheduled'
            else:
                post.scheduled_time = None
                post.status = 'draft'
                
            post.save()
            return redirect('drafts')
            
    return render(request, 'core/edit_draft.html', {'post': post})  

@login_required
def integrations_settings(request):
    org = request.user.owned_organizations.first()
    if not org:
        return redirect('dashboard')

    # If the user is saving a new token
    if request.method == 'POST':
        platform = request.POST.get('platform')
        access_token = request.POST.get('access_token')
        account_id = request.POST.get('account_id')

        # update_or_create updates the token if it exists, or creates a new row if it doesn't
        PlatformIntegration.objects.update_or_create(
            organization=org,
            platform=platform,
            defaults={
                'access_token': access_token,
                'account_id': account_id,
                'is_active': True
            }
        )
        return redirect('integrations_settings')

    # Pull existing connections to display on the page
    active_integrations = org.integrations.filter(is_active=True)
    # Turn it into a quick lookup list for the HTML template
    connected_platforms = [integration.platform for integration in active_integrations]

    context = {
        'org_name': org.name,
        'connected_platforms': connected_platforms,
        'active_integrations': active_integrations,
    }
    return render(request, 'core/settings.html', context)