import re

with open('accounts/urls.py', 'r') as f:
    urls_content = f.read()

if 'verify_otp' not in urls_content:
    urls_content = urls_content.replace(
        "path('logout/',             views.logout_view,  name='logout'),",
        "path('logout/',             views.logout_view,  name='logout'),\n    path('verify-otp/',         views.verify_otp,   name='verify_otp'),"
    )
    with open('accounts/urls.py', 'w') as f:
        f.write(urls_content)

with open('accounts/views.py', 'r') as f:
    views_content = f.read()

if 'def verify_otp' not in views_content:
    # Add verify_otp view
    new_methods = """
from .models import OTPVerification
from django.utils import timezone

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        # Create OTP
        OTPVerification.objects.filter(user=user, action='login').delete()
        otp = OTPVerification.objects.create(user=user, action='login')
        otp.generate_otp()
        request.session['pre_otp_user_id'] = user.pk
        request.session['next_url'] = request.GET.get('next', 'accounts:dashboard')
        return redirect('accounts:verify_otp')
    return render(request, 'accounts/login.html', {'form': form})

def verify_otp(request):
    user_id = request.session.get('pre_otp_user_id')
    if not user_id:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        try:
            otp_record = OTPVerification.objects.get(user_id=user_id, action='login', is_verified=False)
            if otp_record.otp_code == otp_code and otp_record.expires_at > timezone.now():
                otp_record.is_verified = True
                otp_record.save()
                
                # Fetch user and login
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=user_id)
                login(request, user)
                
                # Cleanup session
                del request.session['pre_otp_user_id']
                next_url = request.session.pop('next_url', 'accounts:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "Invalid or expired OTP.")
        except OTPVerification.DoesNotExist:
            messages.error(request, "No valid OTP request found.")
            
    return render(request, 'accounts/verify_otp.html')

"""
    # Replace existing login_view
    views_content = re.sub(
        r'def login_view\(request\):.*?return render\(request, \'accounts/login\.html\', {\'form\': form}\)\n',
        new_methods,
        views_content,
        flags=re.DOTALL
    )
    with open('accounts/views.py', 'w') as f:
        f.write(views_content)
