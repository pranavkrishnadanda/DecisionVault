from django.urls import path

from app.slack import router

urlpatterns = [
    path("integrations", router.integrations, name="slack-integrations"),
    path("install", router.install, name="slack-install"),
    path("callback", router.callback, name="slack-callback"),
    path("channels", router.channels, name="slack-channels"),
    path("messages", router.messages, name="slack-messages"),
    path("test", router.send_test, name="slack-test"),
    path("events", router.events, name="slack-events"),
]
