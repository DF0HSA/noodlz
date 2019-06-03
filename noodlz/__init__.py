import datetime
import functools
import json
import re
import os.path

from flask import Flask, url_for, redirect, request, render_template, session, abort


app = Flask(__name__)
app.config.from_envvar('NOODLZ_SETTINGS')

DESTINATIONS = {}
RE_USER = re.compile('^[A-Za-z_][A-Za-z0-9-_]{,31}$')
DATA_DIR = app.config.get('DATA_DIR', '.')


def reload():
	global DESTINATIONS
	if not os.path.isdir(DATA_DIR):
		os.mkdir(DATA_DIR)
	if not os.path.isdir(DATA_DIR + "/trips"):
		os.mkdir(DATA_DIR + "/trips")
	try:
		with open(os.path.join(DATA_DIR, "destinations.json"), "r") as f:
			DESTINATIONS = json.load(f)
	except FileNotFoundError:
		DESTINATIONS = {}

reload()


def load_trips(date, empty=False):
	'''
	[
		{"user": <str>, "destination": <str>, "orders": [
			{"user": <str>, "order": <str>},
		]}, ...
	]
	'''
	date = datetime.datetime.strptime(date, "%Y-%m-%d").date().isoformat()
	try:
		with open(os.path.join(DATA_DIR, 'trips', date + ".json"), 'r') as f:
			trips = json.load(f)
	except FileNotFoundError:
		if empty:
			trips = []
		else:
			raise
	return date, trips


def save_trips(date, trips):
	date = datetime.datetime.strptime(date, "%Y-%m-%d").date().isoformat()
	with open(os.path.join(DATA_DIR, 'trips', date + ".json"), 'w') as f:
		json.dump(trips, f, indent='  ')


def update_orders(orders, user, item, count):
	n = 0
	for order in orders:
		if order["user"] == user and order["order"] == item:
			if n >= count:
				pass
			else:
				n += 1
				yield order
		else:
			yield order
	for i in range(n, count):
		yield {"user": user, "order": item}


def require_user(f):
	@functools.wraps(f)
	def wrapper(*args, **kwargs):
		if 'user' not in session:
			return render_template('login.html', **kwargs)
		else:
			return f(*args, **kwargs)
	return wrapper


@app.route("/")
def index():
	today = datetime.datetime.now().date().isoformat()
	return redirect(url_for("get_date", date=today))


@app.route("/favicon.ico")
def favicon():
	return app.send_static_file('favicon.ico')


@app.route("/login", methods=['POST'])
def post_login():
	if not RE_USER.match(request.form["user"]):
		abort(400, "Invalid username. Start with a letter, alphanumeric, length between 1 and 32 characters.")
	session['user'] = request.form["user"]
	if 'date' in request.args:
		redirect_date = request.args['date']
	else:
		redirect_date = datetime.datetime.now().date().isoformat()
	return redirect(url_for("get_date", date=redirect_date))


@app.route("/logout", methods=['GET', 'POST'])
def get_logout():
	del session['user']
	if 'date' in request.args:
		redirect_date = request.args['date']
	else:
		redirect_date = datetime.datetime.now().date().isoformat()
	return redirect(url_for("get_date", date=redirect_date))


@app.route("/reload")
def get_reload():
	reload()
	return "OK"


@app.route("/<date>/", methods=["GET"])
@require_user
def get_date(date):
	date, trips = load_trips(date, True)
	if datetime.datetime.strptime(date, "%Y-%m-%d").weekday() != 0:
		return render_template("notmonday.html")

	my_orders = [{} for _ in trips]
	for trip_i, trip in enumerate(trips):
		for order in trip.get("orders", []):
			if order["user"] == session["user"]:
				my_orders[trip_i].setdefault(order["order"], 0)
				my_orders[trip_i][order["order"]] += 1

	return render_template("date.html",
		user=session["user"],
		date=date,
		trips=trips,
		my_orders=my_orders,
		order_accepted="order_accepted" in request.args,
		destinations=DESTINATIONS,
	)


@app.route("/<date>/trip/<int:trip_id>/order", methods=["POST"])
@require_user
def post_order(date, trip_id):
	date, trips = load_trips(date, True)
	trip = trips[trip_id]
	if trip.get("closed", False):
		abort(400, "This trip is already closed.")
	orders = trip.setdefault("orders", [])
	for item, count in request.form.to_dict().items():
		if item.startswith("item-"):
			item = item.replace("item-", "", 1)
			trip["orders"] = list(update_orders(trip.get("orders", []), session["user"], item, int(count)))
	save_trips(date, trips)
	return redirect(url_for("get_date", date=date, order_accepted=True))


@app.route("/<date>/trip/<int:trip_id>/close", methods=["POST"])
@require_user
def post_trip_close(date, trip_id):
	date, trips = load_trips(date, True)
	trip = trips[trip_id]
	if session["user"] != trip["user"]:
		abort(403, "You can't close someone else's trip.")
	trip["closed"] = True
	save_trips(date, trips)
	return redirect(url_for("get_orders", date=date, trip_id=trip_id))


@app.route("/<date>/trip", methods=["POST"])
@require_user
def post_trip(date):
	date, trips = load_trips(date, True)
	trip = {"user": session["user"], "destination": request.form["destination"]}
	trips.append(trip)
	save_trips(date, trips)
	return redirect(url_for("get_date", date=date))


@app.route("/<date>/trip/<int:trip_id>")
@require_user
def get_orders(date, trip_id):
	date, trips = load_trips(date)
	trip = trips[trip_id]
	destination_menu = DESTINATIONS[trip["destination"]]["options"]

	if session["user"] != trip["user"]:
		abort(403, "You can't read someone else's order list.")

	orders = {}
	for order in trip.get("orders", []):
		order_item = order["order"]
		if order_item in orders:
			order_element = orders[order_item]
		else:
			order_element = orders.setdefault(order_item, {"order": order_item, "count": 0, "users": []})
		order_element["count"] += 1
		order_element["users"].append(order["user"])
	order_list = list(sorted(orders.values(), key=lambda o: o["order"]))
	total = sum(destination_menu[o["order"]]["price"] * o["count"] for o in order_list)
	return render_template("orders.html",
		user=session["user"],
		date=date,
		trip_id=trip_id,
		orders=order_list,
		show_users="users" in request.args,
		destination=trip["destination"],
		destinations=DESTINATIONS,
		total=total,
	)
