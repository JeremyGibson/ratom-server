from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.db.models import F

from simple_history.models import HistoricalRecords
from elasticsearch_dsl import Index
from django_elasticsearch_dsl_drf.wrappers import dict_to_obj

YMD_HMS = "%Y-%m-%d %H:%M:%S"


class User(AbstractUser):
    ARCHIVIST = "AR"
    RESEARCHER = "RE"

    USER_TYPE = [
        (ARCHIVIST, "Archivist"),
        (RESEARCHER, "Researcher"),
    ]
    user_type = models.CharField(max_length=2, choices=USER_TYPE,)


class Account(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self) -> str:
        return str(self.title)

    @property
    def total_messages_in_account(self):
        return self.files.aggregate(models.Sum("reported_total_messages")).get(
            "reported_total_messages__sum", 0
        )

    @property
    def total_processed_messages(self):
        return self.messages.filter(audit__processed=True).count()

    @property
    def account_last_modified(self):
        return self.files.latest("date_imported").date_imported

    def get_inclusive_dates(self, str_fmt: str = YMD_HMS, as_string=True):
        dates = []
        for f in self.files.all():
            dates.extend(f.inclusive_dates)
        dates.sort()
        if as_string:
            return f"{dates[0].strftime(str_fmt)} - {dates[-1].strftime(str_fmt)}"
        return dates[0], dates[-1]

    def get_account_status(self):
        if self.files.filter(import_status=File.IMPORTING).count() > 0:
            return File.IMPORTING
        if self.files.filter(import_status=File.FAILED).count() > 0:
            return File.FAILED
        if self.files.filter(import_status=File.CREATED).count() > 0:
            return File.CREATED
        return File.COMPLETE


class RatomFileManager(models.Manager):
    def reported_totals(self, account_title: str) -> models.QuerySet:
        qs = self.get_queryset()
        return qs.filter(account__title=account_title).aggregate(
            models.Sum("reported_total_messages")
        )


class File(models.Model):
    CREATED = "CR"
    IMPORTING = "IM"
    COMPLETE = "CM"
    FAILED = "FA"
    IMPORT_STATUS = [
        (CREATED, "Created"),
        (IMPORTING, "Importing"),
        (COMPLETE, "Complete"),
        (FAILED, "Failed"),
    ]

    account = models.ForeignKey(Account, related_name="files", on_delete=models.CASCADE)
    filename = models.CharField(max_length=200)
    original_path = models.CharField(max_length=500)
    reported_total_messages = models.IntegerField(null=True)
    accession_date = models.DateField(null=True)
    file_size = models.BigIntegerField(null=True)
    md5_hash = models.CharField(max_length=32)
    import_status = models.CharField(
        max_length=2, choices=IMPORT_STATUS, default=CREATED
    )
    date_imported = models.DateTimeField(auto_now_add=True)
    errors = JSONField(null=True, blank=True)

    # Managers
    objects = models.Manager()
    counts = RatomFileManager()

    class Meta:
        unique_together = ["account", "filename"]

    def __str__(self):
        return f"{self.account.title}-{self.filename}"

    @property
    def percent_complete(self) -> object:
        pass

    @property
    def inclusive_dates(self):
        """
        Returns the inclusive
        :param str_format:
        :return:
        """
        qs = self.message_set.filter(sent_date__isnull=False)
        return qs.first().sent_date, qs.last().sent_date


class RestrictionAuthority(models.Model):
    authorities = ArrayField(base_field=models.CharField(max_length=128, blank=True))


class Redaction(models.Model):
    redacted_subject = models.TextField(blank=True)
    redacted_body = models.TextField(blank=True)


class Label(models.Model):
    USER = "U"
    IMPORTER = "I"
    STATIC = "S"
    LABEL_TYPE = [
        (USER, "User"),
        (IMPORTER, "Importer"),
        (STATIC, "Static"),
    ]
    type = models.CharField(max_length=1, choices=LABEL_TYPE,)

    name = models.CharField(max_length=64)

    def __str__(self):
        return f"{self.type}:{self.name}"

    class Meta:
        unique_together = ["type", "name"]


class MessageAudit(models.Model):
    processed = models.BooleanField(default=False)
    is_record = models.BooleanField(default=True, null=True)
    date_processed = models.DateTimeField(null=True)
    restrictions = models.ForeignKey(
        RestrictionAuthority, null=True, on_delete=models.PROTECT
    )
    redactions = models.ForeignKey(Redaction, null=True, on_delete=models.PROTECT)
    labels = models.ManyToManyField(Label)
    updated_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT)
    history = HistoricalRecords()


class Message(models.Model):
    """A model to store individual email messages.
    The unique item in this model is the data field which will be a fairly
    complex data structure.
    """

    source_id = models.CharField(max_length=256)
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    account = models.ForeignKey(
        Account, related_name="messages", on_delete=models.CASCADE
    )
    audit = models.OneToOneField(MessageAudit, on_delete=models.CASCADE)
    sent_date = models.DateTimeField(null=True)
    msg_from = models.TextField(blank=True)
    msg_to = models.TextField(blank=True)
    msg_cc = models.TextField(blank=True)
    msg_bcc = models.TextField(blank=True)
    subject = models.TextField(blank=True)
    body = models.TextField(blank=True)
    directory = models.TextField(blank=True)
    headers = JSONField(null=True, blank=True)
    errors = JSONField(null=True, blank=True)
    inserted_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_date"]

    @property
    def account_indexing(self):
        """Account data (nested) for indexing.
        Example:
            >>> mapping = {
            >>>     "account": {
            >>>         "title": "Gov Purdue"
            >>>     }
            >>> }

        :return:
        """
        return dict_to_obj({"title": self.account.title,})

    @property
    def labels_indexing(self):
        return list(self.audit.labels.values_list("name", flat=True))

    def __str__(self):
        return f"{self.subject[:40]}..."


def upload_directory_path(instance, filename):
    """
    This is just stubbed out based on django examples. Will need to plan
    how this will work with S3.
    :param instance:
    :param filename:
    :return:
    """
    return f"/attachments/{instance.hashed_name}"


class Attachments(models.Model):
    """A model to track email attachments
    Attributes:
        message: the message to which it was attached
        file_name: it's reported filename
        hashed_name: the md5 hash value of the binary (used for storage and dedupe)
        mime_type: the reported mime_type of the attachment
        upload = the location of the file (S3, local, ???).
    """

    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=256, blank=True)
    hashed_name = models.CharField(max_length=32, blank=False)
    mime_type = models.CharField(max_length=128)
    upload = models.FileField(upload_to=upload_directory_path)

    def __str__(self):
        return self.file_name
