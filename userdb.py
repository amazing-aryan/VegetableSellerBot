import logging
import pymongo
import dns
import vegetables
import datetime
import os

uri = uri = os.getenv('uri')
conn_password = os.getenv('dbpass')

client = pymongo.MongoClient(conn_string)
user_db = client['users'].posts
order_db = client['orders'].posts

class UserDB:

    def __init__(self, user_id, orders=[], cart=[], referrals=0, discount_availed=0, cart_last_updated=datetime.datetime.utcnow()):
        self.user_id = user_id
        self.cart = cart
        self.orders = orders
        self.referrals = referrals
        self.discount_availed = discount_availed
        self.cart_last_updated = cart_last_updated
##        self.new_order = new_order
        
    def create_user(self, dic):
        pass

    def to_post(self):
        post_data = {
            'user_id':self.user_id,
            'cart':self.cart,
            'orders':self.orders,
            'no_of_referrals': self.referrals,
            'discount_availed': self.discount_availed,
            'cart_last_updated': self.cart_last_updated
##            'new':self.new_order
            }

        return post_data

    
    def __str__(self):
        return f'user_id:{self.user_id}\ncart:{self.cart}\norders:{self.orders}\nno_0f_referrals:{self.referrals}\ndiscount_availed:{self.discount_availed}\ncart_last_updated:{self.cart_last_updated}'      
        
        

class Order:

    def __init__(self, user_id, cart, address, total, contact, name, payment_id, delivered=False):
        self.user_id = user_id
        self.items = cart
        self.total = total
        self.address = address
        self.contact = contact
        self.name = name
        self.pay_id = payment_id
        self.delivered = delivered

    def to_post(self):
        post_data = {
            'user_id':self.user_id,
            'items':self.items,
            'address':self.address,
            'contact':self.contact,
            'name':self.name,
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
    return UserDB(user_id=data['user_id'], orders=data['orders'],cart=data['cart'], referrals=data['no_of_referrals'], discount_availed=data['discount_availed'], cart_last_updated=data['cart_last_updated'])

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

    update_cart_last_updated_timestamp(user_id)

    return get_user(user_id)

def remove_from_cart(user_id, item_name):
    user_db.find_one_and_update({'user_id':user_id, 'cart':{'$elemMatch':{'item':item_name}}}, {'$pull':{'cart':{'item':item_name}}})
    update_cart_last_updated_timestamp(user_id)
    
def get_cart(user_id):
    user = get_user(user_id)
    return user.cart

def place_order(user_id, cart, address, total, contact, name, pay_id):
    user = get_user(user_id)
    order = Order(user_id, cart, address, total, contact, name, pay_id)
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

def update_referrals(user_id):
    user_db.find_one_and_update({'user_id':user_id}, {"$inc":{'no_of_referrals': 1}})
    pass

def avail_discount(user_id):
    #reflect discount in total
    user_db.find_one_and_update({'user_id':user_id}, {"$inc":{'discount_availed': 1}})
    user_db.find_one_and_update({'user_id':user_id}, {"$set":{'no_of_referrals': 0}})

def clear_cart(user_id):
    user_db.find_one_and_update({'user_id':user_id}, {"$set":{'cart': []}})

def update_cart_last_updated_timestamp(user_id):
    user_db.find_one_and_update({'user_id':user_id}, {"$set":{"last_updated": datetime.datetime.utcnow()}})
    
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
    place_order(u.user_id, cart, 'my address', cart_total(cart),'consumer1', '123', 'cod')
    print(order_db.find())
    print('^^^OrderDB >>> after order')
    print(get_user('123'))
    avail_discount(u.user_id)
    print('^^^OrderDB >>> after discount')
    print(get_user('123'))
    update_referrals(u.user_id)
    clear_cart(u.user_id)
    print('^^^OrderDB >>> after clearing cart')
    print(get_user('123'))