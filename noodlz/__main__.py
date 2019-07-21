import argparse
import decimal
import getpass

from passlib import pwd
from passlib.hash import bcrypt

from . import db, User, Destination, Item


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

	args = ap.parse_args()
	args.func(args)


if __name__ == '__main__':
	main()
