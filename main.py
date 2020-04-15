import os
import random
import userdb
import vegetables
import util

from ka import keep_alive

import cryptg
from telethon import TelegramClient, events, types, custom, utils, errors
import telethon
import logging
logging.basicConfig(filename='log.txt', filemode='w')


BOT_TOKEN = os.getenv('tok')
API_ID = int(os.getenv('api_id'))
API_HASH = os.getenv('api_hash')
bot = TelegramClient('seller', API_ID, API_HASH)

DELIVERY_CHARGE = 50
MIN_ORDER_AMT = 300

# From https://stackoverflow.com/questions/61154990/how-to-get-button-callbackquery-in-conversations-of-telethon-library


def press_event(user_id):
    return events.CallbackQuery(func=lambda e: e.sender_id == user_id)

def message_event(user_id):
    return events.NewMessage(func=lambda e: e.sender_id == user_id)

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply('Hello, here\'s what we sell')

    db = userdb.instantiate(event.sender_id)

    await categories_handler(event)


@bot.on(events.NewMessage(pattern='/categories'))
async def categories_handler(event):
    values_list = set(vegetables.sheet.col_values(2))

    message = "These are the categories that we offer: \n"
    for i, item in enumerate(values_list):
        message = f'{message}\n{i+1}. {item}\n/category_{item}'

    await event.reply(message)


@bot.on(events.NewMessage(pattern=r'/category_\w+'))
async def category_handler(event):
    print('In category handler')
    category = event.message.text.split('_')[1]
    print(category)

    message = f'Here are the items we have in {category}:\n'

    veg_list = vegetables.veg_from_category(category)
    print(veg_list)

    for i, item in enumerate(veg_list):
        message = f'{message}\n{i+1}. **{item.name}**\n**Price**: KES{item.price}\n/item_{item.name}\n'

    await event.reply(message)


@bot.on(events.NewMessage(pattern=r'/item_\w+'))
async def item_handler(event):
    item = event.message.text.split('_')[1]
    veg = vegetables.Vegetable(item)

    message = f'**{veg.name}**\nPrice: KES{veg.price}\n\n/add_to_cart_{veg.name}'

    await event.reply(message, file=veg.image)


@bot.on(events.NewMessage(pattern=r'/add_to_cart_\w+'))
async def cart_handler(event):
    item = event.message.text.split('_')[-1]
    SENDER = event.sender_id
    async with bot.conversation(SENDER) as conv:
        await conv.send_message(f'Enter the number of items of {item} to be added')
        buttons = [[],[]]
        for i in range(1, 11):
            if i<6:
                ind=0
            else:
                ind=1
            buttons[ind].append(telethon.custom.Button.inline(str(i), str(i)))
        await conv.send_message('Choose', buttons=buttons)

        press = await conv.wait_event(press_event(SENDER))
        quantity = int(press.data)
        price = vegetables.Vegetable(item).price
        logging.info(f'Add to cart: Item-{item}, Price-{price}, Quantity-{quantity}')

        userdb.add_to_cart(SENDER, item, int(price), int(quantity))
        await conv.send_message(f'{quantity} {item}(s) added to your cart\n/view_cart')


@bot.on(events.NewMessage(pattern=r'/view_cart'))
async def view_handler(event):
    cart = userdb.get_cart(event.sender_id)
    message = f'Here is your cart: \n\n**Item**\t**Quantity**\t**Price**'

    price = 0
    for item in cart:
        message = f'{message}\n{item["item"]}\t{item["quantity"]}\t{item["price"]}\n/remove_{item["item"]}'
        price += int(item["price"])
    message = f'{message}\n\n**Total number of items**: {len(cart)}\n**Total price:** __KES__{price}\n**Add items:** /categories\n**Place Order**: /place_order'

    await event.reply(message)
    return (cart, price)

@bot.on(events.NewMessage(pattern=r'/remove_\w+'))
async def remove_handler(event):
    sender = event.sender_id
    item = event.message.text.split('_')[1]
    logging.info(f'{sender} removed {item}')
    userdb.remove_from_cart(sender, item)
    await event.reply(f'{item} removed from cart\n/view_cart')

@bot.on(events.NewMessage(pattern=r'/place_order'))
async def order_handler(event):
    cart, price = await view_handler(event)

    if int(price)<MIN_ORDER_AMT:
        await event.reply(f'The minimum order amount for delivery is KES{MIN_ORDER_AMT}. Please add more items to your cart and then order')        
    else:
        SENDER = event.sender_id
        async with bot.conversation(SENDER) as conv:
            await conv.send_message(f'Enter the address where delivery is to be made: ')
            address = await conv.wait_event(message_event(SENDER))
            address = address.message.text

            await conv.send_message(f'Enter your mobile number: ')
            contact = await conv.wait_event(message_event(SENDER))
            contact = contact.message.text

            total = price+DELIVERY_CHARGE
            await conv.send_message(f'**Order amount:** KES{price}\n**Delivery Charges:** KES{DELIVERY_CHARGE}\n**Total:** {total}')
            await conv.send_message('How would you like to pay?', buttons=[
                telethon.custom.Button.inline('Pay Now', '1'),
                telethon.custom.Button.inline('Pay on Delivery', '2')]
                )

            pay_option = await conv.wait_event(press_event(SENDER))
            pay_option = int(pay_option.data)

            if pay_option==1:
                paid, payment_id = util.take_payment(SENDER, total)
                if paid:
                    await conv.send_message('Your order is successful. Please wait for the delivery')
                    userdb.place_order(SENDER, cart, address, total, contact, payment_id)
                else:
                    await conv.send_message('Your payment was unsuccessful :(\nPlease try again')
            elif pay_option==2:
                await conv.send_message('Prove that you are not a robot')
                num1 = random.randint(1,10)
                num2 = random.randint(1,10)
                ans = num1+num2

                opt1 = telethon.custom.Button.inline(str(ans), ans)
                opt2 = telethon.custom.Button.inline(str(ans-6), ans-6)
                opt3 = telethon.custom.Button.inline(str(ans+6), ans+6)
                options = [opt1, opt2, opt3]
                random.shuffle(options)

                await conv.send_message(f'What is {num1}+{num2}?', buttons=options)

                choice = await conv.wait_event(press_event(SENDER))
                if int(choice.data)!=ans:
                    await conv.send_message('Wrong answer. Please try again.')
                else:
                    await conv.send_message('Order placed. Please wait for your delivery')
                    userdb.place_order(SENDER, cart, address, total, contact, 'cod')


keep_alive()
bot.start(bot_token=BOT_TOKEN)
print('Started running')
bot.run_until_disconnected()