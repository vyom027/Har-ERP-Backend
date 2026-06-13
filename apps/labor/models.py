import hashlib
import secrets
from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.utils import timezone


def normalize_mobile(raw):
    """Canonical mobile form: digits only, strip +, spaces, dashes, leading 0/91."""
    if not raw:
        return ''
    digits = ''.join(c for c in str(raw) if c.isdigit())
    # Drop common India country code / trunk prefixes to a 10-digit core when possible
    if len(digits) > 10 and digits.startswith('91'):
        digits = digits[-10:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    return digits


class Labor(models.Model):
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    joining_date = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    # Worker portal login
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='labor_profile'
    )
    is_activated = models.BooleanField(default=False)
    login_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def login_mobile(self):
        """Number used as portal username — prefer whatsapp, fall back to phone."""
        return normalize_mobile(self.whatsapp or self.phone)

    @property
    def portal_status(self):
        if not self.is_activated:
            return 'not_set'
        if not self.login_enabled:
            return 'revoked'
        return 'active'

    @property
    def total_earned(self):
        from apps.production.models import WorkEntry
        from apps.samples.models import Sample
        production_earned = WorkEntry.objects.filter(labor=self).aggregate(total=Sum('total_amount'))['total'] or 0
        samples_earned = Sample.objects.filter(labor=self).aggregate(total=Sum('total_amount'))['total'] or 0
        return production_earned + samples_earned

    @property
    def total_paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def pending_balance(self):
        return self.total_earned - self.total_paid

class Payment(models.Model):
    PAYMENT_TYPES = [
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('other', 'Other'),
    ]
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='cash')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.labor.name} - {self.amount} ({self.payment_date})"


class LaborSetupToken(models.Model):
    """One-time, hashed-at-rest, time-limited token for worker PIN setup."""
    labor = models.ForeignKey(Labor, on_delete=models.CASCADE, related_name='setup_tokens')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    EXPIRY_HOURS = 48

    @staticmethod
    def hash_token(raw):
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def issue(cls, labor):
        """Invalidate any prior unused tokens, create a new one, return the RAW token."""
        cls.objects.filter(labor=labor, used_at__isnull=True).delete()
        raw = secrets.token_urlsafe(32)
        cls.objects.create(
            labor=labor,
            token_hash=cls.hash_token(raw),
            expires_at=timezone.now() + timezone.timedelta(hours=cls.EXPIRY_HOURS),
        )
        return raw

    @classmethod
    def resolve(cls, raw):
        """Return a valid (unused, unexpired) token for the raw value, or None."""
        if not raw:
            return None
        try:
            tok = cls.objects.select_related('labor').get(token_hash=cls.hash_token(raw))
        except cls.DoesNotExist:
            return None
        if tok.used_at is not None or tok.expires_at < timezone.now():
            return None
        return tok

    def consume(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])
