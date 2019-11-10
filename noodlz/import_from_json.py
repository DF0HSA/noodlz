import argparse
import datetime
import json
import os.path

from passlib import pwd
from passlib.hash import bcrypt

from . import db, User, Destination, Item, Trip, Order


def import_from_json(args):
	'''Transfer from the old JSON format (destinations.json and trips/${DATE}.json)
	Caution: If anyone ever changed the prices, that would have affected all past orders, settled or unsettled.'''
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
	ap = argparse.ArgumentParser(help="Migrate from the old JSON format")
	ap.add_argument('destinations', help="destinations.json")
	ap.add_argument('trip', nargs='*', help="any number of trip json files")
	args = ap.parse_args()

	import_from_json(args)
