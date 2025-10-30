import sys
import os
from dotenv import load_dotenv

# 1. Load env variables FIRST
load_dotenv()

import django
from django.conf import settings

# 2. Configure Django SECOND (before any Cashfree stuff)
settings.configure(
    DEBUG=os.getenv('DEBUG', 'True') == 'True',
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-this'),
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=os.getenv('ALLOWED_HOSTS', '*').split(','),
    INSTALLED_APPS=[
        'django.contrib.contenttypes',
        'django.contrib.auth',
        'django.contrib.sessions',
        'django.contrib.messages',
    ],
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    ],
    TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['.'],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    }],
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        }
    },
    MEDIA_URL='/media/',
    MEDIA_ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media'),
)

# 3. Setup Django
django.setup()

# 4. NOW import Cashfree and set config
import uuid
from datetime import date, timedelta
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta

# 5. Set Cashfree config NOW (after Django.setup() and load_dotenv())
Cashfree.XClientId = os.getenv('CASHFREE_CLIENT_ID')
Cashfree.XClientSecret = os.getenv('CASHFREE_CLIENT_SECRET')
cashfree_env = os.getenv('CASHFREE_ENVIRONMENT', 'sandbox')
Cashfree.XEnvironment = Cashfree.SANDBOX if cashfree_env == 'sandbox' else Cashfree.PRODUCTION
X_API_VERSION = "2023-08-01"

# 6. Import Django components (after Django.setup())
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.db import models, connection
from django import forms
from django.urls import path
from django.core.wsgi import get_wsgi_application
from django.conf.urls.static import static

# 7. NOW add your Models, Views, etc.
# ... rest of your code

class Bug(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, default='Open')
    created_by = models.CharField(max_length=100)
    group = models.ForeignKey('BugGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='bugs')
    start_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.IntegerField(null=True, blank=True)
    attachment = models.CharField(max_length=500, null=True, blank=True)  # Store file path
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = '__main__'
        db_table = 'bugs'
class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, default='free')  # free, basic, premium
    bugs_per_day = models.IntegerField(default=1)
    bugs_used_today = models.IntegerField(default=0)
    last_reset_date = models.DateField(auto_now_add=True)
    subscription_expires = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = '__main__'
        db_table = 'user_subscriptions'

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=200, unique=True)
    payment_session_id = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    plan = models.CharField(max_length=20)  # basic or premium
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = '__main__'
        db_table = 'payments'



class BugGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_groups')
    members = models.ManyToManyField(User, related_name='bug_groups', blank=True)
    admins = models.ManyToManyField(User, related_name='admin_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = '__main__'
        db_table = 'bug_groups'

class GroupInvitation(models.Model):
    group = models.ForeignKey(BugGroup, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = '__main__'
        db_table = 'group_invitations'

# Create tables function
# Create tables function
def create_tables():
    with connection.cursor() as cursor:
        try:
            # Create bugs table
                                # Add these inside create_tables() function after existing CREATE TABLE statements

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    plan VARCHAR(20) DEFAULT 'free',
                    bugs_per_day INTEGER DEFAULT 1,
                    bugs_used_today INTEGER DEFAULT 0,
                    last_reset_date DATE,
                    subscription_expires DATE,
                    created_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    order_id VARCHAR(200) UNIQUE,
                    payment_session_id VARCHAR(200),
                    amount DECIMAL(10,2),
                    plan VARCHAR(20),
                    status VARCHAR(50) DEFAULT 'pending',
                    created_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bugs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200),
                    description TEXT,
                    status VARCHAR(20),
                    created_by VARCHAR(100),
                    group_id INTEGER,
                    start_date DATETIME,
                    due_date DATETIME,
                    estimated_hours INTEGER,
                    attachment VARCHAR(500),
                    created_at DATETIME,
                    FOREIGN KEY (group_id) REFERENCES bug_groups(id)
                )
            ''')
            
            # Rest of tables same as before...
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bug_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200),
                    description TEXT,
                    created_by_id INTEGER,
                    created_at DATETIME,
                    FOREIGN KEY (created_by_id) REFERENCES auth_user(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bug_groups_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buggroup_id INTEGER,
                    user_id INTEGER,
                    role VARCHAR(50) DEFAULT 'member',
                    FOREIGN KEY (buggroup_id) REFERENCES bug_groups(id),
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bug_groups_admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buggroup_id INTEGER,
                    user_id INTEGER,
                    FOREIGN KEY (buggroup_id) REFERENCES bug_groups(id),
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER,
                    invited_by_id INTEGER,
                    invited_user_id INTEGER,
                    status VARCHAR(20),
                    created_at DATETIME,
                    FOREIGN KEY (group_id) REFERENCES bug_groups(id),
                    FOREIGN KEY (invited_by_id) REFERENCES auth_user(id),
                    FOREIGN KEY (invited_user_id) REFERENCES auth_user(id)
                )
                           
            ''')
            
            
            # Add missing columns
            try:
                cursor.execute('ALTER TABLE bug_groups_members ADD COLUMN role VARCHAR(50) DEFAULT "member"')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE bugs ADD COLUMN start_date DATETIME')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE bugs ADD COLUMN due_date DATETIME')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE bugs ADD COLUMN estimated_hours INTEGER')
            except:
                pass
            
            try:
                cursor.execute('ALTER TABLE bugs ADD COLUMN attachment VARCHAR(500)')
            except:
                pass
            
            connection.commit()
            print("✓ All tables created/updated successfully")
        except Exception as e:
            print(f"Table creation: {e}")

def get_or_reset_subscription(user_id):
    """Get subscription and reset daily bug count if needed"""
    with connection.cursor() as cursor:
        cursor.execute('SELECT plan, bugs_per_day, bugs_used_today, last_reset_date, subscription_expires FROM user_subscriptions WHERE user_id = %s', [user_id])
        row = cursor.fetchone()
        
        if not row:
            cursor.execute('''
                INSERT INTO user_subscriptions (user_id, plan, bugs_per_day, bugs_used_today, last_reset_date, created_at) 
                VALUES (%s, 'free', 1, 0, date('now'), datetime('now'))
            ''', [user_id])
            return {'plan': 'free', 'bugs_per_day': 1, 'bugs_used_today': 0, 'subscription_expires': None}
        
        plan, bugs_per_day, bugs_used_today, last_reset_date, subscription_expires = row
        
        # Fix: Handle date conversion properly
        if isinstance(last_reset_date, str):
            last_reset = date.fromisoformat(last_reset_date)
        elif isinstance(last_reset_date, date):
            last_reset = last_reset_date
        else:
            last_reset = date.today()
        
        if subscription_expires:
            if isinstance(subscription_expires, str):
                expires = date.fromisoformat(subscription_expires)
            elif isinstance(subscription_expires, date):
                expires = subscription_expires
            else:
                expires = None
        else:
            expires = None
        
        # Check if subscription expired
        if expires and date.today() > expires:
            cursor.execute('''
                UPDATE user_subscriptions 
                SET plan = 'free', bugs_per_day = 1, bugs_used_today = 0, subscription_expires = NULL 
                WHERE user_id = %s
            ''', [user_id])
            return {'plan': 'free', 'bugs_per_day': 1, 'bugs_used_today': 0, 'subscription_expires': None}
        
        # Reset daily count if new day
        if last_reset < date.today():
            cursor.execute('''
                UPDATE user_subscriptions 
                SET bugs_used_today = 0, last_reset_date = date('now') 
                WHERE user_id = %s
            ''', [user_id])
            bugs_used_today = 0
        
        return {
            'plan': plan,
            'bugs_per_day': bugs_per_day,
            'bugs_used_today': bugs_used_today,
            'subscription_expires': expires
        }


# Views
def home(request):
    if request.method == 'POST':
        if 'signup' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            User.objects.create_user(username=username, password=password)
            return redirect('/')
        elif 'login' in request.POST:
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
        elif 'logout' in request.POST:
            logout(request)
    
    # Get user's groups
    with connection.cursor() as cursor:
        if request.user.is_authenticated:
            cursor.execute('''
                SELECT g.id, g.name, g.description, g.created_by_id
                FROM bug_groups g
                INNER JOIN bug_groups_members m ON g.id = m.buggroup_id
                WHERE m.user_id = %s
            ''', (request.user.id,))
            groups = [{'id': row[0], 'name': row[1], 'description': row[2], 'created_by_id': row[3]} for row in cursor.fetchall()]
        else:
            groups = []
    
    pending_invitations = GroupInvitation.objects.filter(invited_user=request.user, status='pending').count() if request.user.is_authenticated else 0
    
    return render(request, 'bugs.html', {
        'groups': groups,
        'pending_invitations': pending_invitations
    })

def group_bugs(request, group_id):
    if not request.user.is_authenticated:
        return redirect('/')
    
    group = get_object_or_404(BugGroup, id=group_id)
    
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM bug_groups_members WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
        is_member = cursor.fetchone()[0] > 0
    
    if not is_member:
        return redirect('/')
    
    subscription = get_or_reset_subscription(request.user.id)
    bugs_remaining = subscription['bugs_per_day'] - subscription['bugs_used_today']
    if subscription['plan'] == 'premium':
        bugs_remaining = -1
    
    if request.method == 'POST':
        if 'add_bug' in request.POST:
            if subscription['plan'] != 'premium' and bugs_remaining <= 0:
                bugs = Bug.objects.filter(group_id=group_id).order_by('-created_at')
                with connection.cursor() as cursor:
                    cursor.execute('SELECT COUNT(*) FROM bug_groups_admins WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
                    is_admin = cursor.fetchone()[0] > 0
                    cursor.execute('''
                        SELECT u.id, u.username, COALESCE(m.role, 'member') as role
                        FROM auth_user u 
                        INNER JOIN bug_groups_members m ON u.id = m.user_id 
                        WHERE m.buggroup_id = %s
                    ''', (group_id,))
                    members = [{'id': row[0], 'username': row[1], 'role': row[2]} for row in cursor.fetchall()]
                
                return render(request, 'group_bugs.html', {
                    'group': group,
                    'bugs': bugs,
                    'members': members,
                    'subscription': subscription,
                    'bugs_remaining': 0,
                    'is_admin': is_admin,
                    'is_creator': group.created_by == request.user,
                    'error': 'Daily bug limit reached! Upgrade your plan to report more bugs.'
                })
            
            if subscription['plan'] != 'premium':
                with connection.cursor() as cursor:
                    cursor.execute('UPDATE user_subscriptions SET bugs_used_today = bugs_used_today + 1 WHERE user_id = %s', [request.user.id])
            
            attachment_path = None
            if 'attachment' in request.FILES:
                uploaded_file = request.FILES['attachment']
                media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media', 'bugs')
                os.makedirs(media_dir, exist_ok=True)
                file_path = os.path.join(media_dir, uploaded_file.name)
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                attachment_path = f'bugs/{uploaded_file.name}'
            
            Bug.objects.create(
                title=request.POST['title'],
                description=request.POST['description'],
                status=request.POST['status'],
                created_by=request.user.username,
                group_id=group_id,
                start_date=request.POST.get('start_date') or None,
                due_date=request.POST.get('due_date') or None,
                estimated_hours=request.POST.get('estimated_hours') or None,
                attachment=attachment_path
            )
            return redirect('group_bugs', group_id=group_id)
        elif 'delete' in request.POST:
            Bug.objects.filter(id=request.POST['bug_id']).delete()
            return redirect('group_bugs', group_id=group_id)
        elif 'leave_group' in request.POST:
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM bug_groups_members WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
                cursor.execute('DELETE FROM bug_groups_admins WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
            return redirect('/')
    
    bugs = Bug.objects.filter(group_id=group_id).order_by('-created_at')
    
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM bug_groups_admins WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
        is_admin = cursor.fetchone()[0] > 0
        
        cursor.execute('''
            SELECT u.id, u.username, COALESCE(m.role, 'member') as role
            FROM auth_user u 
            INNER JOIN bug_groups_members m ON u.id = m.user_id 
            WHERE m.buggroup_id = %s
        ''', (group_id,))
        members = [{'id': row[0], 'username': row[1], 'role': row[2]} for row in cursor.fetchall()]
    
    return render(request, 'group_bugs.html', {
        'group': group,
        'bugs': bugs,
        'members': members,
        'subscription': subscription,
        'bugs_remaining': bugs_remaining,
        'is_admin': is_admin,
        'is_creator': group.created_by == request.user
    })

def notifications(request):
    if not request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        invitation_id = request.POST.get('invitation_id')
        action = request.POST.get('action')
        invitation = get_object_or_404(GroupInvitation, id=invitation_id, invited_user=request.user)
        
        if action == 'accept':
            invitation.status = 'accepted'
            invitation.save()
            # Add user to group
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO bug_groups_members (buggroup_id, user_id) VALUES (%s, %s)', (invitation.group.id, request.user.id))
        elif action == 'reject':
            invitation.status = 'rejected'
            invitation.save()
        
        return redirect('notifications')
    
    invitations = GroupInvitation.objects.filter(invited_user=request.user, status='pending')
    return render(request, 'notifications.html', {'invitations': invitations})

def create_group(request):
    if not request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        group = BugGroup.objects.create(
            name=request.POST['name'],
            description=request.POST['description'],
            created_by=request.user
        )
        # Add creator as member and admin
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO bug_groups_members (buggroup_id, user_id) VALUES (%s, %s)', (group.id, request.user.id))
            cursor.execute('INSERT INTO bug_groups_admins (buggroup_id, user_id) VALUES (%s, %s)', (group.id, request.user.id))
        return redirect('/')
    
    return render(request, 'create_group.html')

def manage_group(request, group_id):
    if not request.user.is_authenticated:
        return redirect('/')
    
    group = get_object_or_404(BugGroup, id=group_id)
    
    # Check if user is admin
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM bug_groups_admins WHERE buggroup_id = %s AND user_id = %s', (group_id, request.user.id))
        is_admin = cursor.fetchone()[0] > 0
    
    if not is_admin:
        return redirect('/')
    
    if request.method == 'POST':
        if 'invite_user' in request.POST:
            username = request.POST['username']
            try:
                user = User.objects.get(username=username)
                with connection.cursor() as cursor:
                    cursor.execute('SELECT COUNT(*) FROM bug_groups_members WHERE buggroup_id = %s AND user_id = %s', (group_id, user.id))
                    is_member = cursor.fetchone()[0] > 0
                
                if not is_member:
                    GroupInvitation.objects.create(
                        group=group,
                        invited_by=request.user,
                        invited_user=user
                    )
            except User.DoesNotExist:
                pass
        elif 'make_admin' in request.POST:
            user_id = request.POST['user_id']
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO bug_groups_admins (buggroup_id, user_id) VALUES (%s, %s)', (group_id, user_id))
        elif 'set_developer' in request.POST:
            user_id = request.POST['user_id']
            with connection.cursor() as cursor:
                cursor.execute('UPDATE bug_groups_members SET role = "developer" WHERE buggroup_id = %s AND user_id = %s', (group_id, user_id))
        elif 'remove_developer' in request.POST:
            user_id = request.POST['user_id']
            with connection.cursor() as cursor:
                cursor.execute('UPDATE bug_groups_members SET role = "member" WHERE buggroup_id = %s AND user_id = %s', (group_id, user_id))
        elif 'remove_member' in request.POST:
            user_id = request.POST['user_id']
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM bug_groups_members WHERE buggroup_id = %s AND user_id = %s', (group_id, user_id))
                cursor.execute('DELETE FROM bug_groups_admins WHERE buggroup_id = %s AND user_id = %s', (group_id, user_id))
        
        return redirect('manage_group', group_id=group_id)
    
    # Get members with roles
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT u.id, u.username, COALESCE(m.role, 'member') as role
            FROM auth_user u 
            INNER JOIN bug_groups_members m ON u.id = m.user_id 
            WHERE m.buggroup_id = %s
        ''', (group_id,))
        members = [{'id': row[0], 'username': row[1], 'role': row[2]} for row in cursor.fetchall()]
        
        cursor.execute('''
            SELECT u.id
            FROM auth_user u 
            INNER JOIN bug_groups_admins a ON u.id = a.user_id 
            WHERE a.buggroup_id = %s
        ''', (group_id,))
        admin_ids = [row[0] for row in cursor.fetchall()]
    
    return render(request, 'manage_group.html', {
        'group': group,
        'members': members,
        'admin_ids': admin_ids,
        'is_creator': group.created_by == request.user
    })

def buy_bugs(request):
    if not request.user.is_authenticated:
        return redirect('/')
    
    if request.method == 'POST':
        plan = request.POST.get('plan')
        
        if plan not in ['basic', 'premium']:
            return redirect('/buy-bugs/')
        
        amount = 5 if plan == 'basic' else 10
        
        try:
            order_id = f"order_{request.user.id}_{uuid.uuid4().hex[:8]}"
            
            customer_details = CustomerDetails(
                customer_id=f"USER{str(request.user.id).zfill(3)}",
                customer_phone="9999999999",
                customer_email=request.user.email or "user@example.com"
            )
            
            # FIXED: Use HTTPS for production
            protocol = "https" if request.is_secure() else "http"
            return_url = f"{protocol}://{request.get_host()}/payment-callback/"
            order_meta = OrderMeta(return_url=return_url)
            
            create_order_request = CreateOrderRequest(
                order_id=order_id,
                order_amount=amount,
                order_currency="INR",
                customer_details=customer_details,
                order_meta=order_meta
            )
            
            print(f"DEBUG: Creating order with return_url: {return_url}")
            api_response = Cashfree().PGCreateOrder(X_API_VERSION, create_order_request, None, None)
            
            Payment.objects.create(
                user=request.user,
                order_id=order_id,
                payment_session_id=api_response.data.payment_session_id,
                amount=amount,
                plan=plan,
                status='pending'
            )
            
            return render(request, 'payment.html', {
                'payment_session_id': api_response.data.payment_session_id,
                'order_id': order_id
            })
            
        except Exception as e:
            print(f"Error creating order: {e}")
            import traceback
            traceback.print_exc()
            return render(request, 'buy_bugs.html', {'error': 'Failed to initiate payment. Please try again.'})
    
    subscription = get_or_reset_subscription(request.user.id)
    return render(request, 'buy_bugs.html', {'subscription': subscription})

def payment_callback(request):
    order_id = request.GET.get('order_id')
    
    if not order_id:
        return redirect('/')
    
    try:
        api_response = Cashfree().PGFetchOrder(X_API_VERSION, order_id, None)
        order_status = api_response.data.order_status
        
        if order_status == 'PAID':
            payment = Payment.objects.get(order_id=order_id)
            payment.status = 'success'
            payment.save()
            
            expires = date.today() + timedelta(days=30)
            bugs_per_day = 5 if payment.plan == 'basic' else -1
            
            with connection.cursor() as cursor:
                cursor.execute('''
                    UPDATE user_subscriptions 
                    SET plan = %s, bugs_per_day = %s, bugs_used_today = 0, subscription_expires = %s, last_reset_date = date('now')
                    WHERE user_id = %s
                ''', [payment.plan, bugs_per_day, expires, payment.user.id])
            
            plan_name = "Basic Plan (5 bugs/day)" if payment.plan == 'basic' else "Premium Plan (Unlimited bugs/day)"
            return render(request, 'payment_success.html', {'plan': plan_name, 'expires': expires})
        else:
            return render(request, 'payment_failed.html', {'message': 'Payment was not completed.'})
    
    except Exception as e:
        print(f"Payment callback error: {e}")
        return render(request, 'payment_failed.html', {'message': 'Error processing payment.'})

# URLs
urlpatterns = [
    path('', home, name='home'),
    path('group/<int:group_id>/', group_bugs, name='group_bugs'),
    path('notifications/', notifications, name='notifications'),
    path('create-group/', create_group, name='create_group'),
    path('manage-group/<int:group_id>/', manage_group, name='manage_group'),
    path('buy-bugs/', buy_bugs, name='buy_bugs'),  # ADD THIS
    path('payment-callback/', payment_callback, name='payment_callback'),  # ADD THIS
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

application = get_wsgi_application()

application = get_wsgi_application()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    import os
    
    # Auto-setup database on first run or when database is too small
    if 'runserver' in sys.argv or 'migrate' in sys.argv:
        if not os.path.exists('db.sqlite3') or os.path.getsize('db.sqlite3') < 50000:
            print("🔧 Setting up database for first time...")
            if 'runserver' in sys.argv:
                # Run migrations first
                execute_from_command_line(['app.py', 'migrate', '--run-syncdb'])
            create_tables()
            print("✅ Database ready!")
    
    execute_from_command_line(sys.argv)
    # At the VERY END of app.py, after all your views

application = get_wsgi_application()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    import sys
    execute_from_command_line(sys.argv)

