from urllib.parse import urlparse

from apps.utils.models import Create
from apps.utils.task_runner import run_task_sync
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _


class ProviderCDK(models.TextChoices):
    OPENAI = 'OA', _('open Ai')
    ANTHROPIC = 'AP', _('anthropic')


class Consumer(models.TextChoices):
    FAST_CHAT = 'FCH', _('чат')
    REMINDER = 'REM', _('системный')
    IMAGE = 'IMG', _('картинка')


class Proxy(models.Model):
    title = models.CharField(_('Название прокси'), max_length=20)
    proxy_socks = models.CharField(_('прокси полный socks'), max_length=400)
    proxy_http = models.CharField(_('прокси полный http'), max_length=400)
    proxy_url = models.CharField(_('прокси формата http://proxy_host:proxy_port'), max_length=200)
    proxy_username = models.CharField(_('прокси username'), max_length=200, blank=True, null=True)
    proxy_password = models.CharField(_('прокси password'), max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = "прокси для соединения"
        verbose_name_plural = "прокси для соединения"

    def __str__(self):
        return self.title

    def clean(self):
        """
        Выполняем общие проверки для всей модели.
        """
        self._validate_proxy_url()
        self._validate_proxy_http()
        self._validate_proxy_socks()

        # Проверка на соответствие логина и пароля
        if (self.proxy_username and not self.proxy_password) or (self.proxy_password and not self.proxy_username):
            raise ValidationError(_("Оба поля 'proxy_username' и 'proxy_password' должны быть заполнены вместе."))

    def _validate_proxy_url(self):
        """
        Проверяем, что proxy_url имеет корректный формат.
        """
        if not self.proxy_url.startswith("http://") and not self.proxy_url.startswith("https://"):
            raise ValidationError(
                _("Поле 'proxy_url' должно начинаться с 'http://' или 'https://'."),
                code='invalid_proxy_url'
            )
        self._validate_url_structure(self.proxy_url, field_name='proxy_url')

    def _validate_proxy_http(self):
        """
        Проверяем, что proxy_http имеет корректный формат.
        """
        if not self.proxy_http.startswith("http://") and not self.proxy_http.startswith("https://"):
            raise ValidationError(
                _("Поле 'proxy_http' должно начинаться с 'http://' или 'https://'"),
                code='invalid_proxy_http'
            )
        self._validate_url_structure(self.proxy_http, field_name='proxy_http')

    def _validate_proxy_socks(self):
        """
        Проверяем, что proxy_socks имеет корректный формат.
        """
        if not self.proxy_socks.startswith("socks5://"):
            raise ValidationError(
                _("Поле 'proxy_socks' должно начинаться с 'socks5://'"),
                code='invalid_proxy_socks'
            )
        self._validate_url_structure(self.proxy_socks, field_name='proxy_socks')

    def _validate_url_structure(self, url, field_name):
        """
        Проверяем общую структуру URL (хост, порт).
        """
        parsed_url = urlparse(url)
        if not parsed_url.hostname or not parsed_url.port:
            raise ValidationError(
                _(f"Поле '{field_name}' должно содержать корректный хост и порт."),
                code=f'invalid_{field_name}'
            )


class UserPrompt(models.Model):
    """
    Модель для хранения промптов, используемых с моделями GPT.

    ### Fields:
    - title (`CharField`): Название промпта.
    - prompt_text (`TextField`): Текст промпта.
    - is_default (`BooleanField`): Флаг установки промпта по умолчанию.
    - consumer (`CharField`): Потребитель запроса.

    ### Methods:
    - clean(*args, **kwargs): Проверяет корректность параметров модели перед сохранением.
    - save(*args, **kwargs): Переопределенный метод сохранения объекта модели для выполнения предварительной проверки перед сохранением.

    """
    title = models.CharField(_('название промпта'), max_length=28)
    prompt_text = models.TextField(_('текст промпта'))
    ru_prompt_text = models.TextField(_('текст промпта на русском'))
    is_default = models.BooleanField(_('по умолчанию'), default=False)
    consumer = models.CharField(_('потребитель запроса'), max_length=3, choices=Consumer, default=Consumer.FAST_CHAT)

    class Meta:
        verbose_name = _('промпт для GPT')
        verbose_name_plural = _('промпты для GPT')

    def __str__(self):
        return self.title

    def clean(self, *args, **kwargs):
        default_model = UserPrompt.objects.filter(is_default=True).exclude(pk=self.pk)
        if not self.is_default and not default_model:
            raise ValidationError('Необходимо указать хотя бы один промпт по умолчанию.')

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_default:
                UserPrompt.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)


class GptModels(models.Model):
    """
    Модель для хранения параметров моделей GPT.

    ### Fields:
    - public_name (`CharField`): Название модели GPT для показа пользователю.
    - title (`CharField`): Имя модели GPT, используемое для выполнения запросов.
    - base_url (`CharField`): URL-адрес, по которому выполняются запросы к модели (опционально).
    - is_default (`BooleanField`): Флаг, указывающий, доступна ли модель всем пользователям по умолчанию.
    - is_free (`BooleanField`): Флаг, указывающий, бесплатна ли модель для пользователей.
    - proxy (`ForeignKey`): Ссылка на объект `Proxy`, используемый для запросов через прокси (опционально).
    - incoming_price (`DecimalField`): Стоимость обработки входящих данных за 100 тысяч токенов.
    - outgoing_price (`DecimalField`): Стоимость обработки исходящих данных за 100 тысяч токенов.
    - token (`CharField`): API-токен для аутентификации запросов к модели.
    - context_window (`IntegerField`): Максимальное количество токенов для передачи контекста (истории) в запросе.
    - max_request_token (`IntegerField`): Максимальное количество токенов, допустимое в одном запросе.
    - time_window (`IntegerField`): Временное окно (в минутах) для передачи истории запросов (по умолчанию 30).
    - consumer (`CharField`): Тип потребителя модели, задаваемый из списка возможных значений (`FAST_CHAT`, и т.д.).

    ### Methods:
    - clean(*args, **kwargs): Проверяет корректность параметров модели перед сохранением.
    - save(*args, **kwargs): Переопределенный метод сохранения объекта модели для выполнения предварительной проверки перед сохранением.

    """
    provider_cdk = models.CharField(_('провайдер CDK'), max_length=2, choices=ProviderCDK, default=ProviderCDK.OPENAI)
    public_name = models.CharField(_('название модели'), max_length=70)
    title = models.CharField(_('модель GPT'), max_length=28)
    base_url = models.CharField(_('base_url'), max_length=200, blank=True, null=True)
    is_default = models.BooleanField(_('доступна всем по умолчанию'), default=False)
    is_free = models.BooleanField(_('бесплатная для пользователя'), default=False)
    proxy = models.ForeignKey(Proxy, on_delete=models.SET_NULL, related_name='model_proxy', null=True, blank=True)
    incoming_price = models.DecimalField(_('стоимость входящих / 100K токенов'), max_digits=6, decimal_places=2, default=0)
    outgoing_price = models.DecimalField(_('стоимость исходящих / 100K токенов'), max_digits=6, decimal_places=2, default=0)
    token = models.CharField(_('токен для запроса'), max_length=200)
    context_window = models.IntegerField(_('окно количества токенов для передачи истории в запросе'))
    max_request_token = models.IntegerField(_('максимальное количество токенов в запросе'))
    time_window = models.IntegerField(_('окно времени для передачи истории в запросе, мин'), default=30)
    consumer = models.CharField(_('потребитель запроса'), max_length=3, choices=Consumer, default=Consumer.FAST_CHAT)

    class Meta:
        verbose_name = _('модель GPT')
        verbose_name_plural = _('модели GPT')

    def __str__(self):
        return self.public_name

    def clean(self, *args, **kwargs):
        default_model = GptModels.objects.filter(is_default=True).exclude(pk=self.pk)
        if not self.is_default and not default_model:
            raise ValidationError('Необходимо указать хотя бы одну модель по умолчанию для всех.')

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_default:
                GptModels.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)


class UserGptModels(models.Model):
    """
    Модель для хранения разрешенных GPT моделей для пользователя.

    ### Fields:
    - user (`OneToOneField`): Пользователь, которому принадлежат модели.
    - active_model (`ForeignKey`, опционально): Активная модель для пользователя.
    - approved_models (`OneToOneField`): Разрешенные модели для пользователя.
    - time_start (`DateTimeField`): Время начала окна для передачи истории.
    - active_prompt (`ForeignKey`, опционально): Активный промпт для пользователя.

    ### Methods:
    - save(*args, **kwargs): Переопределенный метод сохранения объекта модели для автоматического назначения активной модели при создании нового объекта.

    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='approved_models')
    active_model = models.ForeignKey(GptModels, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_for_users', verbose_name=_('активная модель'))
    approved_models = models.ManyToManyField(to=GptModels, related_name='approved_users')
    time_start = models.DateTimeField(_('время начала окна для передачи истории'), default=now)
    active_prompt = models.ForeignKey(UserPrompt, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_for_user', verbose_name=_('активный промпт'))

    class Meta:
        verbose_name = _('разрешенная GPT модели юзера')
        verbose_name_plural = _('разрешенные GPT модели юзера')

    def __str__(self):
        return f'User: {self.user}, Active model: {self.active_model}'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super(UserGptModels, self).save(*args, **kwargs)

        if not self.active_model:
            default_model = GptModels.objects.filter(is_default=True).first()
            if default_model:
                self.active_model = default_model
                self.save(update_fields=['active_model'])

        if not self.active_prompt:
            default_prompt = UserPrompt.objects.filter(is_default=True).first()
            if default_prompt:
                self.active_prompt = default_prompt
                self.save(update_fields=['active_prompt'])

        if is_new and default_model:
            if not self.approved_models.filter(id=default_model.id).exists():
                self.approved_models.add(default_model)


class TextTransactions(Create):
    """
    Модель для хранения истории вопросов и ответов AI.

    ### Fields:
    - user (`ForeignKey`): Пользователь, связанный с историей.
    - room_group_name (`CharField`): ID комнаты клиента.
    - question (`TextField`): Вопрос, заданный пользователем.
    - question_tokens (`PositiveIntegerField`): Количество токенов в вопросе (может быть null).
    - question_token_price (`DecimalField`): Стоимость исходящих токенов.
    - answer (`TextField`): Ответ, сгенерированный AI.
    - answer_tokens (`PositiveIntegerField`): Количество токенов в ответе (может быть null).
    - answer_token_price (`DecimalField`): Стоимость входящих.
    - consumer (`CharField`): Потребитель запроса.
    - model (`ForeignKey`): Генеративная модель.
    - image (`ImageField`): Картинка.

    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='history_ai', null=True, blank=True)
    room_group_name = models.CharField(_('WEB чат'), max_length=128, null=True, blank=True)
    question = models.TextField(_('Вопрос'))
    question_tokens = models.PositiveIntegerField(null=True)
    question_token_price = models.DecimalField(_('стоимость исходящих / 100K токенов'), max_digits=6, decimal_places=2, default=0)
    image_url = models.CharField(_('url картинки для анализа'), max_length=1280, null=True, blank=True)
    answer = models.TextField(_('Ответ'))
    answer_tokens = models.PositiveIntegerField(null=True)
    answer_token_price = models.DecimalField(_('стоимость входящих / 100K токенов'), max_digits=6, decimal_places=2, default=0)
    consumer = models.CharField(_('потребитель запроса'), max_length=3, choices=Consumer, default=Consumer.FAST_CHAT)
    model = models.ForeignKey(GptModels, on_delete=models.SET_NULL, null=True, blank=True, related_name='history_ai')
    image = GenericRelation(
        "filehub.MediaAttachment",
        related_query_name="generations",
    )

    class Meta:
        verbose_name = _('История запросов к ИИ')
        verbose_name_plural = _('История запросов к ИИ')
        ordering = ('created_at',)

    def __str__(self):
        return f'User: {self.user}, Question: {self.question}, Consumer: {self.consumer}'


class UploadedScanImage(Create):
    """Модель для хранения изображений, загруженных пользователями."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scan_images")
    chat_id = models.BigIntegerField()
    image = models.ImageField(upload_to="scan/")
    caption = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Image by {self.user} in chat {self.chat_id}"


def delete_image(instance):
    """Удаляет изображение (локально или из S3)."""
    from utils.tasks import delete_image_in_bucket

    if instance.image:
        run_task_sync(delete_image_in_bucket, instance.image.url)


@receiver(pre_delete, sender=UploadedScanImage)
def delete_post_image_pre(sender, instance, **kwargs):
    """Удаляет изображение перед удалением объекта (если delete() вызван напрямую)."""
    delete_image(instance)


@receiver(post_delete, sender=UploadedScanImage)
def delete_post_image_post(sender, instance, **kwargs):
    """Удаляет изображение после удаления объекта (если delete() вызван через QuerySet)."""
    delete_image(instance)
