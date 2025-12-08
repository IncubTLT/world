from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.utils.tasks import send_email_msg


def send_activation_email(email, code):
    context = {
        "subject": _("Код подтверждения: {code}").format(code=code),
        "body": _("Ваш код подтверждения для входа на сайт {domain}.").format(domain=settings.DOMAIN),
        "code": str(code),
    }
    if settings.DEBUG:
        async_to_sync(send_email_msg)(email, context, "welcome")
    else:
        async_to_sync(send_email_msg.kiq)(email, context, "welcome")
