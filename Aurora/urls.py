from django.conf import settings
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Social auth urls
    url('', include('social_django.urls', namespace='social')),
    # Aurora urls
    url(r'^$', 'cloud.views.pages.index', name='home'),
    url(r'^not_implemented/$', 'cloud.views.pages.not_implemented',
        name='not_implemented'),
    url(r'^cloud/', include('cloud.urls')),

    # Django Admin
    url(r'^admin/', include(admin.site.urls)),

    # User login/logout
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        {'template_name': 'pages-login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        {'template_name': 'pages-logout.html'}),
    url(r'^accounts/login-error/$', 'cloud.views.pages.login_error',
        name='login_error'),
)

