import argparse
import datetime
import decimal
import getpass
import json
import os.path

from passlib import pwd
from passlib.hash import bcrypt

from . import db, User, Destination, Item, Trip, Order


def createdb(args):
	db.create_all()


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


def item_add(args):
	destination = Destination.query.filter_by(id=args.destination).first()
	item = Item(name=args.name, destination=destination, price=args.price, tag=args.tag)
	db.session.add(item)
	db.session.commit()
	print(f"Item id: {item.id}")


def import_(args):
	user_cache = {}
	def get_user(name):
		if name in user_cache:
			return user_cache[name]
		user = User.query.filter_by(name=name).first()
		if user is not None:
			return user
		user_pass = pwd.genword(128, charset='ascii_50')
		user = User(name=name, pass_hash=bcrypt.hash(user_pass))
		print(f"Generated user={name} pass={user_pass}")
		db.session.add(user)
		return user

	dest_cache = {}
	with open(args.destinations, 'r') as f:
		destinations = json.load(f)
		for dest_name, dest_data in destinations.items():
			dest = Destination(name=dest_data.get("title", dest_name))
			db.session.add(dest)
			dest_item_cache = dest_cache[dest_name] = {'__dest': dest}
			for item_name, item_data in dest_data.get("options", {}).items():
				item_title = item_data.get("title", item_name)
				for option in item_data.get("options", []):
					item_title += ";" + option
				item = Item(
					name=item_title,
					tag=item_data.get("id", None),
					price=item_data["price"],
					destination=dest
				)
				db.session.add(item)
				dest_item_cache[item_name] = item

	print(args.trip)
	for trip_filename in args.trip:
		with open(trip_filename, 'r') as f:
			trip_filename_base, _ = os.path.splitext(os.path.basename(trip_filename))
			trips = json.load(f)
			for trip_data in trips:
				trip_dest_cache = dest_cache[trip_data["destination"]]
				trip = Trip(
					date=datetime.datetime.strptime(trip_filename_base, '%Y-%m-%d').date(),
					closed=trip_data.get("closed", False),
					destination=trip_dest_cache["__dest"],
					user=get_user(trip_data["user"])
				)
				db.session.add(trip)
				for order_data in trip_data.get("orders", []):
					order = Order(
						settled=order_data.get("paid", False),
						item=trip_dest_cache[order_data["order"]],
						trip=trip,
						user=get_user(order_data["user"])
					)
					db.session.add(order)

	db.session.commit()


def main():
	ap = argparse.ArgumentParser()
	ap.set_defaults(func=lambda *args: ap.print_usage())
	ap_commands = ap.add_subparsers(dest='command', required=True)

	ap_createdb = ap_commands.add_parser('createdb')
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

	ap_item_add = ap_item_commands.add_parser('add')
	ap_item_add.add_argument('destination', type=int)
	ap_item_add.add_argument('name')
	ap_item_add.add_argument('price', type=decimal.Decimal)
	ap_item_add.add_argument('--tag', default=None)
	ap_item_add.set_defaults(func=item_add)

	# Import
	ap_import = ap_commands.add_parser('import')
	ap_import.add_argument('destinations', help="destinations.json")
	ap_import.add_argument('trip', nargs='*', help="any number of trip json files")
	ap_import.set_defaults(func=import_)

	args = ap.parse_args()
	args.func(args)


if __name__ == '__main__':
	main()
