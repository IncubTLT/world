import logging

import aiosmtplib
from asgiref.sync import sync_to_async
from config.taskiq_app import taskiq_broker
from django.conf import settings
from django.core import mail, management
from django.core.mail import get_connection
from django.forms import ValidationError
from templated_email import get_templated_mail

logger = logging.getLogger(__name__)


@taskiq_broker.task
async def send_email_msg(
    to_email: str | list[str],
    context: dict,
    template: str,
):
    try:

        if isinstance(to_email, str):
            to_list = [to_email]
        else:
            to_list = list(to_email or [])
        if not to_list:
            raise ValidationError({"error": "Recipient list is empty."})

        email_message = get_templated_mail(
            template_name=template,
            from_email=settings.EMAIL_HOST_USER,
            to=to_list,
            context=context
        )

        connection = get_connection()
        host = connection.host
        port = connection.port
        username = connection.username
        password = connection.password

        result = await aiosmtplib.send(
            email_message.message(),
            sender=email_message.from_email,
            recipients=email_message.to,
            hostname=host,
            port=port,
            username=username,
            password=password,
            use_tls=True,
            start_tls=False,
        )
        logger.debug(f"Результат отправки email: {result}")
    except aiosmtplib.SMTPRecipientsRefused as error:
        raise ValidationError({"error": "Invalid email address."}) from error
    except aiosmtplib.SMTPAuthenticationError as error:
        raise ValidationError({"error": "Authentication failed. Check your SMTP credentials."}) from error
    except aiosmtplib.SMTPSenderRefused as error:
        raise ValidationError({"error": "Sender address rejected. Check your email settings."}) from error
    except aiosmtplib.SMTPException as error:
        raise ValidationError({"error": "SMTP error occurred. Please try again later."}) from error


@taskiq_broker.task(schedule=[{"cron": "45 23 * * *"}])
async def backup():
    """Дамп базы данных."""
    management.call_command('dbbackup', clean=True)
    logger.info('Database backup has been created')


async def send_email_msg_attachments(
    to_emails: str | list[str],
    context: dict,
    template: str,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> int:
    to_list = [to_emails] if isinstance(to_emails, str) else list(to_emails or [])
    if not to_list:
        raise ValidationError({"error": "Recipient list is empty."})

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    email_message = get_templated_mail(
        template_name=template,
        from_email=from_email,
        to=to_list,
        context=context,
    )
    if context and context.get("subject"):
        email_message.subject = context["subject"]

    for filename, content, mimetype in (attachments or []):
        email_message.attach(filename, content, mimetype)

    connection = get_connection()
    email_message.connection = connection
    backend_path = f"{connection.__class__.__module__}.{connection.__class__.__name__}"

    try:
        sent = await sync_to_async(email_message.send)(fail_silently=False)

        if backend_path.startswith("django.core.mail.backends.locmem"):
            logger.info("Email sent to outbox (locmem). outbox_len=%s", len(mail.outbox))

        logger.info(
            "Email sent via %s: to=%s attachments=%d sent=%s",
            backend_path,
            ", ".join(to_list),
            len(attachments or []),
            sent,
        )
        if sent < 1:
            raise ValidationError({"error": "Email backend returned 0 (nothing sent)."})
        return sent
    except Exception as e:
        logger.exception("Email send failed via %s: %r", backend_path, e)
        raise
