import gspread
from google.oauth2.service_account import Credentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)

gc = gspread.authorize(credentials)

sheet = gc.open("Vegetables Data").sheet1
orders = gc.open("Vegetables Orders Data").sheet1

class Vegetable:

  def __init__(self, name):
    self.name = name
    cell = sheet.find(name)
    row = cell.row

    self.price = sheet.cell(row, 3).value
    self.category = sheet.cell(row, 2).value
    self.image = sheet.cell(row, 4).value

def veg_from_category(cat):
  items_list = sheet.findall(cat)

  veg_list = []
  for item in items_list:
    row = item.row
    name = sheet.cell(row, 1).value
    veg = Vegetable(name)
    veg_list.append(veg)

  return veg_list

def add_order(order):
    values = []
    for value in order.__dict__:
        values.append(str(order.__dict__[value]))
    print(values)
    _id = values[-1]
    del values[-1]
    values.insert(0, _id)
    orders.append_row(values=values)

if __name__=='__main__':
    add_order()
