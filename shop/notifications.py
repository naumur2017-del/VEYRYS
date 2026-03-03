from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import OrderNotification


def _build_order_items(order):
    return list(order.items.select_related('product').all())


def build_admin_order_message(order):
    lines = [
        'NOUVELLE COMMANDE VEYRYS',
        f'Reference: #{order.id}',
        f"Date: {order.created.strftime('%Y-%m-%d %H:%M')}",
        '',
        'Client:',
        f'- Nom: {order.first_name} {order.last_name}',
        f'- Email: {order.email}',
        f'- Telephone: {order.phone}',
        f'- Ville: {order.city}',
        f'- Adresse: {order.address}',
        '',
        'Details commande:',
    ]
    for item in _build_order_items(order):
        lines.append(
            f'- {item.quantity} x {item.product.name} '
            f'(Taille: {item.selected_size}, Couleur: {item.selected_color}) '
            f'= {item.get_cost():,.0f} FCFA'
        )

    lines.append('')
    lines.append(f'TOTAL: {order.get_total_cost():,.0f} FCFA')
    return '\n'.join(lines)


def build_customer_order_message(order):
    lines = [
        'CONFIRMATION DE COMMANDE VEYRYS',
        f'Reference: #{order.id}',
        '',
        f'Bonjour {order.first_name},',
        'Nous vous confirmons la bonne reception de votre commande.',
        'Notre equipe va la traiter dans les plus brefs delais.',
        '',
        'Recapitulatif de votre commande:',
    ]
    for item in _build_order_items(order):
        lines.append(
            f'- {item.quantity} x {item.product.name} '
            f'(Taille: {item.selected_size}, Couleur: {item.selected_color}) '
            f'= {item.get_cost():,.0f} FCFA'
        )

    lines.append('')
    lines.append(f'TOTAL: {order.get_total_cost():,.0f} FCFA')
    lines.append('')
    lines.append('Merci pour votre confiance.')
    lines.append('VEYRYS - Le Sublime Raisonnable')
    return '\n'.join(lines)


def _send_order_email(recipient, subject, text_message, template_name, template_context, provider_label):
    sender = (
        settings.DEFAULT_FROM_EMAIL
        or settings.EMAIL_HOST_USER
        or settings.ADMIN_ORDER_EMAIL
    )

    if not sender:
        return {
            'ok': False,
            'provider': provider_label,
            'response_body': '',
            'error_message': (
                'Configuration email manquante. Definir EMAIL_HOST_USER '
                'ou DEFAULT_FROM_EMAIL.'
            ),
            'recipient': recipient,
        }

    html_message = render_to_string(template_name, template_context)

    try:
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=sender,
            to=[recipient],
        )
        email_message.attach_alternative(html_message, 'text/html')
        _attach_logo_inline_if_exists(email_message)
        email_message.send(fail_silently=False)

        return {
            'ok': True,
            'provider': provider_label,
            'response_body': 'emails_sent=1',
            'error_message': '',
            'recipient': recipient,
        }
    except Exception as exc:
        return {
            'ok': False,
            'provider': provider_label,
            'response_body': '',
            'error_message': str(exc),
            'recipient': recipient,
        }


def _attach_logo_inline_if_exists(email_message):
    logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo.png'
    if not logo_path.exists():
        return
    with logo_path.open('rb') as logo_file:
        logo_mime = MIMEImage(logo_file.read())
    logo_mime.add_header('Content-ID', '<veyrys-logo>')
    logo_mime.add_header('Content-Disposition', 'inline', filename='logo.png')
    email_message.attach(logo_mime)


def _log_notification(order, message, send_result):
    return OrderNotification.objects.create(
        order=order,
        recipient=send_result['recipient'],
        provider=send_result['provider'],
        status='sent' if send_result['ok'] else 'failed',
        message_preview=message[:1000],
        response_body=send_result['response_body'][:4000],
        error_message=send_result['error_message'],
    )


def notify_admin_of_order(order):
    order_items = _build_order_items(order)
    total_cost = order.get_total_cost()
    message = build_admin_order_message(order)
    send_result = _send_order_email(
        recipient=settings.ADMIN_ORDER_EMAIL,
        subject=f'Nouvelle commande VEYRYS #{order.id}',
        text_message=message,
        template_name='shop/email/admin_order_notification.html',
        template_context={
            'order': order,
            'order_items': order_items,
            'total_cost': total_cost,
            'logo_cid': 'veyrys-logo',
        },
        provider_label='email_smtp_admin',
    )
    return _log_notification(order, message, send_result)


def notify_customer_of_order(order):
    order_items = _build_order_items(order)
    total_cost = order.get_total_cost()
    message = build_customer_order_message(order)
    send_result = _send_order_email(
        recipient=order.email,
        subject=f'Confirmation de votre commande VEYRYS #{order.id}',
        text_message=message,
        template_name='shop/email/customer_order_confirmation.html',
        template_context={
            'order': order,
            'order_items': order_items,
            'total_cost': total_cost,
            'logo_cid': 'veyrys-logo',
        },
        provider_label='email_smtp_customer',
    )
    return _log_notification(order, message, send_result)
