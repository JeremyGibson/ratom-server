from enum import Enum
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from simple_history.models import HistoricalRecords
from elasticsearch_dsl import Index

from ratom.managers import MessageManager


class FileImportStatus(Enum):
    CREATED = "Created"
    IMPORTING = "Importing"
    COMPLETE = "Complete"
    FAILED = "Failed"


class UserTEnum(Enum):
    ARCHIVIST = "Archivist"
    RESEARCHER = "Researcher"


class RecordStatus(Enum):
    NON_RECORD = "Non Record"
    RECORD = "Record"
    RECORD_RES = "Restricted Record"
    RECORD_RED = "Redacted Record"


class User(AbstractUser):
    user_type = models.CharField(
        max_length=32, choices=[(tag, tag.value) for tag in UserTEnum]
    )


class Account(models.Model):
    title = models.CharField(max_length=200)
    history = HistoricalRecords()

    def __str__(self) -> str:
        return str(self.title)


class File(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    filename = models.CharField(max_length=200)
    reported_total_messages = models.IntegerField(null=True)
    accession_date = models.DateField(null=True)
    file_size = models.IntegerField(null=True)
    md5_hash = models.CharField(max_length=32)
    import_status = models.CharField(
        max_length=32,
        choices=[(tag, tag.value) for tag in FileImportStatus],
        default=FileImportStatus.CREATED,
    )
    history = HistoricalRecords()

    @property
    def percent_complete(self) -> object:
        pass


# Keeping this in place since some GraphQl items depend at the moment.
# This is however deprecated based on current modeling.
class Processor(models.Model):
    processed = models.BooleanField(default=False)
    is_record = models.BooleanField(default=True)
    has_pii = models.BooleanField(default=False)
    date_processed = models.DateTimeField(null=True)
    date_modified = models.DateTimeField(null=True)
    last_modified_by = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True
    )


class RestrictionAuthority(models.Model):
    authorities = ArrayField(base_field=models.CharField(max_length=128, blank=True))


class Redaction(models.Model):
    redacted_subject = models.TextField(null=True)
    redacted_body = models.TextField(null=True)


class MessagesNotProcessed(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_record__is_null=True)


class MessagesHaveRestrictions(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(restrictions__is_null=False)


class Message(models.Model):
    """A model to store individual email messages.
    The unique item in this model is the data field which will be a fairly
    complex data structure.

    EXAMPLE:
        data= {
            headers: [{
                string: string,
                ...,
            }],
            labels: {
                nlp: [{
                    string: string,
                    ...,
                }],
                user: [{
                    string: string,
                    ...,
                }],
            },
            errors: [{
                int: string,
            }],
            raw: string ## Text dump of an errored message,
        }
    """

    source_id = models.CharField(max_length=256, blank=True)
    file = models.ForeignKey(File, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    restrictions = models.ForeignKey(
        RestrictionAuthority, null=True, on_delete=models.CASCADE
    )
    redaction = models.ForeignKey(Redaction, null=True, on_delete=models.CASCADE)
    is_record = models.BooleanField(null=True)
    sent_date = models.DateTimeField(null=True)
    msg_from = models.TextField(null=True)
    msg_to = models.TextField(null=True)
    msg_cc = models.TextField(blank=True)
    msg_bcc = models.TextField(blank=True)
    msg_subject = models.TextField(blank=True)
    msg_body = models.TextField(blank=True)
    directory = models.TextField(blank=True)
    data = JSONField(null=True, blank=True)
    history = HistoricalRecords()

    # Managers
    objects = models.Manager()
    unprocessed = MessagesNotProcessed()
    restricted = MessagesHaveRestrictions()


def upload_directory_path(instance, filename):
    """
    This is just stubbed out based on django examples. Will need to plan
    how this will work with S3.
    :param instance:
    :param filename:
    :return:
    """
    return f"{instance.message.pk}/{instance.hashed_name}"


class Attachments(models.Model):
    """A model to track email attachments
    Attributes:
        message: the message to which it was attached
        file_name: it's reported filename
        hashed_name: the md5 hash value of the binary (used for storage and dedupe)
        mime_type: the reported mime_type of the attachment
        upload = the location of the file (S3, local, ???).
    """

    message = models.ForeignKey(Message, on_delete=models.PROTECT)
    file_name = models.CharField(max_length=256, blank=True)
    hashed_name = models.CharField(max_length=32, blank=False)
    mime_type = models.CharField(max_length=64)
    upload = models.FileField(upload_to=upload_directory_path)
