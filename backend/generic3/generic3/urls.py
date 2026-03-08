from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path, include, reverse
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import REDIRECT_FIELD_NAME
from two_factor.admin import AdminSiteOTPRequired, AdminSiteOTPRequiredMixin
from two_factor.urls import urlpatterns as tf_urls
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import resolve_url
from django.contrib.auth.views import redirect_to_login



class CustomAdminSiteOTPRequired(AdminSiteOTPRequired):
    def login(self, request, extra_context=None):
        redirect_to = request.POST.get(
            REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME)
        )
        if request.method == "GET" and super(
            AdminSiteOTPRequiredMixin, self
        ).has_permission(request):
            if request.user.is_verified():
                index_path = reverse("admin:index", current_app=self.name)
            else:
                index_path = reverse("two_factor:setup", current_app=self.name)
            return HttpResponseRedirect(index_path)

        if not redirect_to or not url_has_allowed_host_and_scheme(
            url=redirect_to, allowed_hosts=[request.get_host()]
        ):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return redirect_to_login(redirect_to)


admin.site.__class__ = CustomAdminSiteOTPRequired

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("authentication.urls")),
    path('', include("modules.urls")),
    path('', include("users.urls")),
    path('', include("clinics.urls")),
    path('', include("medications.urls")),
    path('', include("activities.urls")),
    path('', include("notifications.urls")),
    path('', include("fileshare.urls")),
    path('', include("questionnaires.urls")),
    path('', include(tf_urls)),

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Add debug toolbar URLs
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
