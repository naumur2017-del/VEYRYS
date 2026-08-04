import hashlib
import hmac
import json
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.urls import reverse

from .models import Order, PaymentTransaction


class PaymentProviderError(RuntimeError):
    pass


class CamerPayError(PaymentProviderError):
    pass


def _failed_statuses():
    return {'failed', 'canceled', 'cancelled', 'expired'}


class CamerPayClient:
    provider = 'CamerPay'

    def __init__(self, request=None):
        self.request = request

    def create_checkout(self, order):
        if not self._use_live_api:
            raise CamerPayError(
                "CamerPay n'est pas configure. Definissez CAMERPAY_API_TOKEN."
            )

        amount = int(order.get_total_cost())
        payload = {
            'amount': amount,
            'currency': settings.CAMERPAY_CURRENCY,
            'customer_phone': order.phone,
            'customer_email': order.email,
            'customer_name': f'{order.first_name} {order.last_name}'.strip(),
            'merchant_invoice_id': str(order.id),
            'merchant_callback_url': self._absolute_url(reverse('shop:camerpay_webhook')),
            'merchant_return_url': self._absolute_url(reverse('shop:payment_return', args=[order.id])),
            'idempotency_key': str(order.id),
            'source': 'veyrys',
        }
        if settings.CAMERPAY_PAYMENT_METHOD:
            payload['payment_method'] = settings.CAMERPAY_PAYMENT_METHOD

        data = self._request('POST', '/api/payment/initiate', payload)
        provider_reference = data.get('transaction_uuid') or data.get('uuid') or ''
        checkout_url = data.get('pay_url') or data.get('redirect_url') or ''
        if not provider_reference or not checkout_url:
            raise CamerPayError(data.get('message') or 'Reponse CamerPay incomplete.')

        transaction, _ = PaymentTransaction.objects.get_or_create(
            order=order,
            provider=self.provider,
            provider_reference=provider_reference,
            defaults={'amount': amount, 'currency': settings.CAMERPAY_CURRENCY},
        )
        transaction.amount = amount
        transaction.currency = settings.CAMERPAY_CURRENCY
        transaction.payment_method = settings.CAMERPAY_PAYMENT_METHOD
        transaction.checkout_url = checkout_url
        transaction.raw_response = data
        transaction.status = self._map_status(data.get('status'), default=PaymentTransaction.Status.INITIATED)
        transaction.save()
        return transaction

    def verify_and_apply(self, *, order, provider_reference):
        if not self._use_live_api:
            raise CamerPayError("CamerPay n'est pas configure.")

        data = self._request('GET', f'/api/payment/{provider_reference}/status')
        transaction_data = data.get('transaction') or data
        status = str(transaction_data.get('status') or data.get('status') or '').lower()

        transaction = order.payments.filter(provider=self.provider, provider_reference=provider_reference).first()
        if transaction is None:
            transaction = PaymentTransaction.objects.create(
                order=order,
                provider=self.provider,
                provider_reference=provider_reference,
                amount=int(order.get_total_cost()),
                currency=settings.CAMERPAY_CURRENCY,
            )
        transaction.payment_method = transaction_data.get('payment_method') or transaction.payment_method
        transaction.raw_response = data
        transaction.status = self._map_status(status)
        transaction.save()

        self._apply_order_status(order, status, provider_reference)
        return transaction

    def apply_webhook(self, form_data):
        provider_reference = form_data.get('uuid', '').strip()
        order_id_raw = form_data.get('invoice_id', '').strip()
        status = form_data.get('status', '').strip().lower()
        amount = form_data.get('amount', '').strip()
        payment_method = form_data.get('payment_method', '').strip()
        signature = form_data.get('signature', '').strip()
        header_signature = ''
        if self.request:
            header_signature = self.request.headers.get('X-CamerPay-Signature', '').strip()

        if not provider_reference or not order_id_raw or not status or not amount:
            raise CamerPayError('Webhook CamerPay incomplet.')

        if settings.CAMERPAY_CALLBACK_SECRET:
            self._verify_signature(
                provider_reference=provider_reference,
                order_reference=order_id_raw,
                status=status,
                amount=amount,
                signature=header_signature or signature,
            )

        try:
            order = Order.objects.get(id=int(order_id_raw))
        except (Order.DoesNotExist, ValueError):
            return None

        try:
            received_amount = int(Decimal(amount))
        except (InvalidOperation, ValueError) as exc:
            raise CamerPayError('Montant CamerPay invalide.') from exc
        if received_amount != int(order.get_total_cost()):
            raise CamerPayError('Montant CamerPay incompatible avec la commande.')

        transaction = order.payments.filter(provider=self.provider, provider_reference=provider_reference).first()
        if transaction is None:
            transaction = PaymentTransaction.objects.create(
                order=order,
                provider=self.provider,
                provider_reference=provider_reference,
                amount=received_amount,
                currency=settings.CAMERPAY_CURRENCY,
            )
        transaction.payment_method = payment_method or transaction.payment_method
        transaction.raw_response = dict(form_data)
        transaction.status = self._map_status(status)
        transaction.save()

        self._apply_order_status(order, status, provider_reference)
        return transaction

    def _apply_order_status(self, order, status, provider_reference):
        if status in {'completed', 'success'} and not order.paid:
            order.paid = True
            order.payment_reference = provider_reference
            order.save(update_fields=['paid', 'payment_reference', 'updated'])

    def _map_status(self, status, default=PaymentTransaction.Status.PENDING):
        status = str(status or '').lower()
        if status in {'completed', 'success'}:
            return PaymentTransaction.Status.SUCCESS
        if status in _failed_statuses():
            return PaymentTransaction.Status.FAILED
        if status in {'pending', 'processing'}:
            return PaymentTransaction.Status.PENDING
        return default

    def _verify_signature(self, *, provider_reference, order_reference, status, amount, signature):
        data = f'{provider_reference}|{order_reference}|{status}|{amount}'
        expected = hmac.new(
            settings.CAMERPAY_CALLBACK_SECRET.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature):
            raise CamerPayError('Signature CamerPay invalide.')

    def _absolute_url(self, path):
        base_url = str(getattr(settings, 'SITE_URL', '')).rstrip('/')
        if base_url and path.startswith('/'):
            return f'{base_url}{path}'
        if self.request:
            return self.request.build_absolute_uri(path)
        return path

    @property
    def _use_live_api(self):
        return bool(settings.CAMERPAY_API_TOKEN)

    def _authorization_header(self):
        token = str(settings.CAMERPAY_API_TOKEN).strip()
        if token.lower().startswith('bearer '):
            return token
        return f'Bearer {token}'

    def _request(self, method, path, payload=None):
        url = f"{settings.CAMERPAY_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                'Authorization': self._authorization_header(),
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': f"VEYRYS/1.0 (+{getattr(settings, 'SITE_URL', '')})",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            raise CamerPayError(f'Erreur CamerPay {exc.code}: {detail}') from exc
        except urllib.error.URLError as exc:
            raise CamerPayError(f'CamerPay indisponible: {exc.reason}') from exc
