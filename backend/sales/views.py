from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Product, Order


@csrf_exempt
def buy_product(request, product_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    with transaction.atomic():
        product = get_object_or_404(
            Product.objects.select_for_update(), id=product_id
        )

        if product.stock <= 0:
            Order.objects.create(product=product, quantity=1, status='failed')
            return JsonResponse({'success': False, 'message': 'Sold out'}, status=400)

        product.stock -= 1
        product.save()

        Order.objects.create(product=product, quantity=1, status='success')

        # Broadcast the new stock count to everyone watching this product
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'stock_{product.id}',
            {
                'type': 'stock_update',
                'remaining_stock': product.stock
            }
        )

        return JsonResponse({
            'success': True,
            'message': 'Purchase successful',
            'remaining_stock': product.stock
        })