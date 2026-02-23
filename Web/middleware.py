import uuid
from datetime import timedelta
from django.utils.timezone import now
from django.conf import settings
from .models import PageView, Session


class AnalyticsMiddleware:
    """
    Middleware to track page views and user sessions for analytics
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip tracking for certain paths
        if self._should_skip_tracking(request):
            return self.get_response(request)

        # Get or create session key
        session_key = self._get_session_key(request)

        # Track page view
        self._track_page_view(request, session_key)

        # Update session
        self._update_session(request, session_key)

        response = self.get_response(request)
        return response

    def _should_skip_tracking(self, request):
        """Skip tracking for static files, admin, API calls, etc."""
        path = request.path_info

        # Skip static/media files
        if path.startswith('/static/') or path.startswith('/media/'):
            return True

        # Skip admin
        if path.startswith('/admin/'):
            return True

        # Skip dashboard (staff only)
        if path.startswith('/dashboard/'):
            return True

        # Skip API endpoints
        if path.startswith('/api/') or 'api' in path:
            return True

        # Skip AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True

        # Skip non-GET requests (only track page views)
        if request.method != 'GET':
            return True

        return False

    def _get_session_key(self, request):
        """Get session key from cookie or create new one"""
        session_key = request.COOKIES.get('analytics_session')

        if not session_key:
            session_key = str(uuid.uuid4())

        return session_key

    def _track_page_view(self, request, session_key):
        """Record a page view"""
        try:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '')

            # Create page view record
            PageView.objects.create(
                url=request.path_info,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                ip_address=ip,
                referrer=request.META.get('HTTP_REFERER', ''),
                session_key=session_key,
                user=request.user if request.user.is_authenticated else None,
            )
        except Exception as e:
            # Don't break the request if analytics fails
            print(f"Analytics error: {e}")

    def _update_session(self, request, session_key):
        """Update or create session record"""
        try:
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', '')

            # Get or create session
            session, created = Session.objects.get_or_create(
                session_key=session_key,
                defaults={
                    'ip_address': ip,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'user': request.user if request.user.is_authenticated else None,
                }
            )

            if not created:
                # Update existing session
                session.last_activity = now()
                session.page_views += 1
                session.is_active = True
                if request.user.is_authenticated:
                    session.user = request.user
                session.save(update_fields=['last_activity', 'page_views', 'is_active', 'user'])
            else:
                # New session starts with 1 page view
                session.page_views = 1
                session.save(update_fields=['page_views'])

        except Exception as e:
            # Don't break the request if analytics fails
            print(f"Session tracking error: {e}")


class SessionCleanupMiddleware:
    """
    Middleware to mark old sessions as inactive
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Clean up old sessions (run this occasionally)
        if hasattr(request, '_session_cleanup_done'):
            return self.get_response(request)

        try:
            # Mark sessions inactive if no activity for 30 minutes
            cutoff = now() - timedelta(minutes=30)
            Session.objects.filter(
                last_activity__lt=cutoff,
                is_active=True
            ).update(is_active=False)
        except Exception as e:
            print(f"Session cleanup error: {e}")

        request._session_cleanup_done = True

        response = self.get_response(request)

        # Set analytics session cookie
        if not request.COOKIES.get('analytics_session'):
            session_key = str(uuid.uuid4())
            response.set_cookie(
                'analytics_session',
                session_key,
                max_age=60*60*24*30,  # 30 days
                httponly=True,
                samesite='Lax'
            )

        return response