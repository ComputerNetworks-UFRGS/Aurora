from django.conf.urls.defaults import patterns, include, url

# Enabling Django contrib admin
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Social auth urls
    url(r'', include('social_auth.urls')),
    # Aurora urls
    url(r'^$', 'manager.views.pages.index', name='home'),
    url(r'^not_implemented/$', 'manager.views.pages.not_implemented',
        name='not_implemented'),
    url(r'^manager/', include('manager.urls')),

    # Django admin docs
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Django admin url
    url(r'^admin/', include(admin.site.urls)),

    # User login/logout
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        {'template_name': 'pages-login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        {'template_name': 'pages-logout.html'}),
    url(r'^accounts/login-error/$', 'manager.views.pages.login_error',
        name='login_error'),

)
