import logging
import pymongo
import dns
import vegetables
import datetime

### Todo
# Cart last updated timestamp
# clear cart
# referral

uri = os.getenv('uri')
conn_password = os.getenv('dbpass')
conn_string = uri.replace("<password>", conn_password)

client = pymongo.MongoClient(conn_string)
user_db = client['users'].posts
order_db = client['orders'].posts

class UserDB:

    def __init__(self, user_id, orders=[], cart=[]):
        self.user_id = user_id
        self.cart = cart
        self.orders = orders
##        self.new_order = new_order
        
    def create_user(self, dic):
        pass

    def to_post(self):
        post_data = {
            'user_id':self.user_id,
            'cart':self.cart,
            'orders':self.orders
##            'new':self.new_order
            }

        return post_data

    
    def __str__(self):
        return f'user_id:{self.user_id}\ncart:{self.cart}\norders:{self.orders}'      
        
        

class Order:

    def __init__(self, user_id, cart, address, total, contact, payment_id, delivered=False):
        self.user_id = user_id
        self.items = cart
        self.address = address
        self.total = total
        self.contact = contact
        self.pay_id = payment_id
        self.delivered = delivered

    def to_post(self):
        post_data = {
            'user_id':self.user_id,
            'items':self.items,
            'address':self.address,
            'contact':self.contact,
            'total':self.total,
            'pay_id':self.pay_id,
            'delivered':self.delivered
            }

        return post_data
        

def instantiate(user_id):
    user = UserDB(user_id)
    try:
        user_db.insert_one(user.to_post())
    except pymongo.errors.DuplicateKeyError:
        logging.info('Duplicate insertion tried')
    return user

def get_user(user_id):
    cursor = user_db.find_one({'user_id':user_id})
    data = {}
    for i, item in enumerate(cursor):
        if i==0:
            continue
        data[item] = cursor[item]
    return UserDB(user_id=data['user_id'], orders=data['orders'],cart=data['cart'])

p=0
def add_to_cart(user_id, item_name, item_price, quantity):
    price = quantity * item_price
    cart = user_db.find_one({'user_id':user_id})
    exists=False
    for item in cart['cart']:
        # print((item))
        if item['item']==item_name:
            # print((item['item']))
            # print(('******'))
            exists=True
            break
    if not exists:
        item = {'item':item_name, 'quantity':quantity, 'price':price}
        user_db.find_one_and_update({'user_id':user_id}, {"$push":{"cart": item}})
    else:
##        p = user_db.find_one({'user_id':user_id, 'cart':{'$elemMatch':{'item':item_name}}})
        
        user_db.find_one_and_update({'user_id':user_id, 'cart':{'$elemMatch':{'item':item_name}}}, {'$inc':{'cart.$.quantity':int(quantity)}})
        user_db.find_one_and_update({'user_id':user_id, 'cart':{'$elemMatch':{'item':item_name}}}, {'$inc':{'cart.$.price':price}})

    return get_user(user_id)

def remove_from_cart(user_id, item_name):
    user_db.find_one_and_update({'user_id':user_id, 'cart':{'$elemMatch':{'item':item_name}}}, {'$pull':{'cart':{'item':item_name}}})
    
def get_cart(user_id):
    user = get_user(user_id)
    return user.cart

def place_order(user_id, cart, address, total, contact, pay_id):
    user = get_user(user_id)
    order = Order(user_id, cart, address, total, contact, pay_id)
    order_id = order_db.insert_one(order.to_post()).inserted_id
    order.id = order_id

    user_db.find_one_and_update({'user_id':user_id}, {'$push':{'orders':order_id}})

    vegetables.add_order(order)

def cart_total(cart):
    total = 0
    for item in cart:
        total += item['price']
    return total

def cart_total_from_user(user_id):
    cart = get_cart(user_id)
    return cart_total(cart)
    
if __name__=='__main__':
    user_db.delete_many({})
    order_db.delete_many({})
    # print((user_db.count_documents({})))
    u = instantiate('123')
    print((u))
    add_to_cart('123', 'kheera', 20, 2)
    # print((get_user('123')))
    add_to_cart(u.user_id, 'lauki', 30, 2)
    t=add_to_cart(u.user_id, 'pyaz', 40, 5)
    # print((t))
    print((get_user('123')))
    remove_from_cart('123','pyaz')
    print('********After removing')
    u = get_user('123')
    print(u)
    cart = get_cart('123')
    place_order(u.user_id, cart, 'my address', cart_total(cart), '123', 'cod')
    print(order_db.find())
    print('^^^OrderDB >>> after order')
    print(get_user('123'))
