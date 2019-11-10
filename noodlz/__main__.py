import argparse
import datetime
import decimal
import getpass


from passlib import pwd
from passlib.hash import bcrypt

from . import db, User, Destination, Item, Trip, Order


def _print_item(item):
	print(f"id={item.id} tag={item.tag} name={item.name} destination={item.destination_id} price={item.price} historical={item.historical}")


def _print_order(o):
	print(f"id={o.id} trip={o.trip.id} date={o.trip.date} buyer={o.trip.user.name} destination={o.trip.destination.name}    item={o.item.name.split(';')[0]} price={o.item.price}    buyer={o.user.name} paid={o.settled}")


def createdb(args):
	db.drop_all()
	db.create_all()
	if args.testdata:
		def add(x):
			db.session.add(x)
			return x

		alice = add(User(name="Alice", pass_hash=bcrypt.hash("password")))
		bob = add(User(name="Bob", pass_hash=bcrypt.hash("password")))
		carol = add(User(name="Carol", pass_hash=bcrypt.hash("password")))
		dave = add(User(name="Dave", pass_hash=bcrypt.hash("password")))

		jen_and_berries = add(Destination(name="Jen and Berries"))
		cakehole = add(Destination(name="Cakehole"))

		cookie_dough = add(Item(name="Cookie Dough", destination=jen_and_berries, tag="CD", price=1.20))
		stracciatella = add(Item(name="Stracciatella", destination=jen_and_berries, tag="S", price=1.00))

		cheesecake = add(Item(name="Cheesecake", destination=cakehole, tag="CC", price=2.50))
		pie = add(Item(name="Pie", destination=cakehole, tag="PI", price=3.14))
		sacher = add(Item(name="Sachertorte", destination=cakehole, tag="ST", price=4.00))

		date1 = datetime.date(1970, 1, 5)
		trip1 = add(Trip(date=date1, destination=jen_and_berries, closed=True, user=alice))
		trip2 = add(Trip(date=date1, destination=cakehole, closed=True, user=bob))

		date2 = datetime.date(1970, 1, 12)
		trip3 = add(Trip(date=date2, destination=jen_and_berries, closed=True, user=alice))

		date3 = datetime.date(1970, 1, 19)
		trip4 = add(Trip(date=date3, destination=jen_and_berries, closed=True, user=carol))
		trip5 = add(Trip(date=date3, destination=cakehole, closed=False, user=bob))

		add(Order(item=cookie_dough, trip=trip1, user=alice, settled=True))
		add(Order(item=cookie_dough, trip=trip1, user=bob, settled=True))
		add(Order(item=stracciatella, trip=trip1, user=carol, settled=True))

		add(Order(item=cheesecake, trip=trip2, user=bob, settled=False))
		add(Order(item=sacher, trip=trip2, user=dave, settled=True))

		add(Order(item=cookie_dough, trip=trip3, user=alice, settled=True))
		add(Order(item=cookie_dough, trip=trip3, user=bob, settled=False))
		add(Order(item=stracciatella, trip=trip3, user=bob, settled=False))
		add(Order(item=stracciatella, trip=trip3, user=carol, settled=True))
		add(Order(item=stracciatella, trip=trip3, user=dave, settled=True))

		add(Order(item=stracciatella, trip=trip4, user=carol, settled=False))
		add(Order(item=cookie_dough, trip=trip4, user=alice, settled=True))
		add(Order(item=stracciatella, trip=trip4, user=alice, settled=False))
		add(Order(item=cookie_dough, trip=trip4, user=dave, settled=False))

		add(Order(item=pie, trip=trip5, user=carol, settled=False))
		add(Order(item=sacher, trip=trip5, user=dave, settled=False))
		db.session.commit()


def user_add(args):
	if args.generate:
		password = pwd.genword(128, charset='ascii_50')
	else:
		password = getpass.getpass("Password: ")
		password_verify = getpass.getpass("Again: ")
		if password != password_verify:
			raise RuntimeError("Passwords don't match.")
	pass_hash = bcrypt.hash(password)
	user = User(name=args.name, pass_hash=pass_hash)
	db.session.add(user)
	db.session.commit()
	print(f"User id: {user.id}")


def destination_add(args):
	destination = Destination(name=args.name)
	db.session.add(destination)
	db.session.commit()
	print(f"Destination id: {destination.id}")


def item_list(args):
	items = Item.query.all()
	for item in items:
		_print_item(item)


def item_add(args):
	destination = Destination.query.filter_by(id=args.destination_id).first()
	item = Item(name=args.name, destination=destination, price=args.price, tag=args.tag)
	db.session.add(item)
	db.session.commit()
	print(f"Item id: {item.id}")


def _item_remove(item):
	if item is None:
		print("No such item.")
		return
	orders = Order.query.filter_by(item=item).filter(Order.trip.has(closed=False)).all()
	if len(orders) > 0:
		print("There are outstanding orders with this item:")
		for o in orders:
			_print_order(o)
		return
	item.historical = True
	db.session.add(item)

def item_remove(args):
	item = Item.query.filter_by(id=args.item_id).first()
	_item_remove(item)
	db.session.commit()


def item_modify(args):
	item = Item.query.filter_by(id=args.item_id).first()
	if item is None:
		print("No such item.")
		return
	if args.name:
		item.name = args.name
	if args.tag:
		item.tag = args.tag
	if args.remove_tag:
		item.tag = None
	db.session.add(item)
	db.session.commit()


def item_reprice(args):
	item = Item.query.filter_by(id=args.item_id).first()
	was_historical = item.historical
	_item_remove(item)
	item_new = Item(name=item.name, tag=item.tag, price=args.price, destination=item.destination, historical=was_historical)
	db.session.add(item)
	db.session.commit()


def order_list(args):
	orders = Order.query.all()
	for o in orders:
		_print_order(o)


def main():
	ap = argparse.ArgumentParser()
	ap.set_defaults(func=lambda *args: ap.print_usage())
	ap_commands = ap.add_subparsers(dest='command', required=True)

	ap_createdb = ap_commands.add_parser('createdb')
	ap_createdb.add_argument('--testdata', action='store_true', default=False)
	ap_createdb.set_defaults(func=createdb)

	# User
	ap_user = ap_commands.add_parser('user')
	ap_user.set_defaults(func=lambda *args: ap_user.print_usage())
	ap_user_commands = ap_user.add_subparsers(dest='user_command', required=True)

	ap_user_add = ap_user_commands.add_parser('add')
	ap_user_add.add_argument('name')
	ap_user_add.add_argument('--generate', action='store_true', default=False, help="Generate a password instead of asking for one")
	ap_user_add.set_defaults(func=user_add)

	# Destination
	ap_destination = ap_commands.add_parser('destination')
	ap_destination.set_defaults(func=lambda *args: ap_destination.print_usage())
	ap_destination_commands = ap_destination.add_subparsers(dest='destination_command', required=True)

	ap_destination_add = ap_destination_commands.add_parser('add')
	ap_destination_add.add_argument('name')
	ap_destination_add.set_defaults(func=destination_add)

	# Item
	ap_item = ap_commands.add_parser('item')
	ap_item.set_defaults(func=lambda *args: ap_item.print_usage())
	ap_item_commands = ap_item.add_subparsers(dest='item_command', required=True)

	# Item List
	ap_item_list = ap_item_commands.add_parser('list')
	ap_item_list.set_defaults(func=item_list)

	# Item Add
	ap_item_add = ap_item_commands.add_parser('add')
	ap_item_add.add_argument('destination_id', type=int)
	ap_item_add.add_argument('name')
	ap_item_add.add_argument('price', type=decimal.Decimal)
	ap_item_add.add_argument('--tag', default=None)
	ap_item_add.set_defaults(func=item_add)

	# Item Modify
	ap_item_modify = ap_item_commands.add_parser('modify', help="It is not allowed to change an existing item's associated destination, or its price, as that would confuse past orders.")
	ap_item_modify.add_argument('item_id', type=int)
	ap_item_modify.add_argument('--name', default=None)
	ap_item_modify.add_argument('--tag', default=None)
	ap_item_modify.add_argument('--remove_tag', action='store_true', default=False)
	ap_item_modify.set_defaults(func=item_modify)

	# Item Reprice
	ap_item_reprice = ap_item_commands.add_parser('reprice', help="Note that this will only mark the item as historical, and create a new item with all properties equal except the new price.")
	ap_item_reprice.add_argument('item_id', type=int)
	ap_item_reprice.add_argument('price', type=decimal.Decimal)
	ap_item_reprice.set_defaults(func=item_reprice)

	# Item Remove
	ap_item_remove = ap_item_commands.add_parser('remove', help="An item can only be removed if there are no open orders of it (else the user would be unable to remove their order) and that the item is only marked 'historical' and will be unorderable in future trips. Past, closed trips remain unaffected.")
	ap_item_remove.add_argument('item_id', type=int)
	ap_item_remove.set_defaults(func=item_remove)

	# Trip
	ap_trip = ap_commands.add_parser('trip')
	ap_trip.set_defaults(func=lambda *args: ap_trip.print_usage())
	ap_trip_commands = ap_trip.add_subparsers(dest='trip_command', required=True)

	# Order
	ap_order = ap_commands.add_parser('order')
	ap_order.set_defaults(func=lambda *args: ap_order.print_usage())
	ap_order_commands = ap_order.add_subparsers(dest='order_command', required=True)

	# Order List
	ap_order_list = ap_order_commands.add_parser('list')
	ap_order_list.set_defaults(func=order_list)

	args = ap.parse_args()
	args.func(args)


if __name__ == '__main__':
	main()
