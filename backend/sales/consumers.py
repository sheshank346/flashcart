import json
from channels.generic.websocket import AsyncWebsocketConsumer


class StockConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.product_id = self.scope['url_route']['kwargs']['product_id']
        self.group_name = f'stock_{self.product_id}'

        # Join the group for this specific product
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # This gets called when someone broadcasts a stock update to this group
    async def stock_update(self, event):
        await self.send(text_data=json.dumps({
            'remaining_stock': event['remaining_stock']
        }))