from django.conf import settings
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Social auth urls
    url('', include('social.apps.django_app.urls', namespace='social')),
    # Aurora urls
    url(r'^$', 'manager.views.pages.index', name='home'),
    url(r'^not_implemented/$', 'manager.views.pages.not_implemented',
        name='not_implemented'),
    url(r'^manager/', include('manager.urls')),

    # Django Admin
    url(r'^admin/', include(admin.site.urls)),

    # User login/logout
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        {'template_name': 'pages-login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        {'template_name': 'pages-logout.html'}),
    url(r'^accounts/login-error/$', 'manager.views.pages.login_error',
        name='login_error'),
)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        # Debug toolbar urls
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )
