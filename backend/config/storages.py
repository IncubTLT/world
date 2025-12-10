from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage, S3StaticStorage


class StaticStorage(S3StaticStorage):
    bucket_name = settings.STATIC_BUCKET_NAME
    default_acl = 'public-read'
    file_overwrite = False
    # custom_domain = '{}.{}'.format(bucket_name, settings.AWS_S3_DOMAIN)


class MediaStorage(S3StaticStorage):
    bucket_name = settings.MEDIA_BUCKET_NAME
    default_acl = 'public-read'
    file_overwrite = False
    # custom_domain = '{}.{}'.format(bucket_name, settings.AWS_S3_DOMAIN)


class DataBaseStorage(S3Boto3Storage):
    default_acl = 'private'
    bucket_name = settings.DATABASE_BUCKET_NAME
    file_overwrite = False
