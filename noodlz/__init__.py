import datetime
import functools
import os
import re

from flask import Flask
from flask import url_for, redirect, render_template, abort
from flask import session, request, g
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy.exc
# import passlib.hash

__version__ = "2.1.2"


app = Flask(__name__)
# setup.py imports __version__ from this module, but it won't have NOODLZ_SETTINGS set. NOODLZ_SETTINGS_IGNORE gives us a workaround for CI.
if 'NOODLZ_SETTINGS' in os.environ or 'NOODLZ_SETTINGS_IGNORE' not in os.environ:
	app.config.from_envvar('NOODLZ_SETTINGS')
app.config['RE_USER'] = re.compile(app.config.get('RE_USER', '^[A-Za-z_][A-Za-z0-9-_]{,31}$'))
db = SQLAlchemy(app)
GLOBAL_PARAMS = {'version': __version__}


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(32), unique=True, nullable=False)
	pass_hash = db.Column(db.String(128), nullable=False)


class Destination(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(128), unique=True, nullable=False)


class Item(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Text(), nullable=False)
	tag = db.Column(db.String(16), default=None, nullable=True)
	price = db.Column(db.Numeric(9, scale=2), nullable=False)
	historical = db.Column(db.Boolean(), default=False, nullable=False)
	destination_id = db.Column(db.Integer, db.ForeignKey('destination.id'))
	destination = db.relationship('Destination', backref=db.backref('items', lazy=True))


class Trip(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	date = db.Column(db.Date(), nullable=False)
	closed = db.Column(db.Boolean(), default=False, nullable=False)
	destination_id = db.Column(db.Integer, db.ForeignKey('destination.id'))
	destination = db.relationship('Destination')
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	user = db.relationship('User', backref=db.backref('trips', lazy=True))
	__table_args__ = (db.UniqueConstraint('user_id', 'date', 'destination_id'),)

	def get_items_grouped(self):
		trip_items = sorted(set(o.item for o in self.orders), key=lambda i: i.id)
		return [{"item": item, "users": [o.user for o in self.orders if o.item == item]} for item in trip_items]

	def get_user_item_count(self, user, item):
		return len([o for o in self.orders if o.user == user and o.item == item])

	def get_item_users(self, item):
		return [o.user for o in self.orders if o.item == item]


class Order(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	settled = db.Column(db.Boolean(), default=False, nullable=False)
	item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
	item = db.relationship('Item')
	trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'))
	trip = db.relationship('Trip', backref=db.backref('orders', lazy=True))
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	user = db.relationship('User', backref=db.backref('orders', lazy=True))


def parse_date(date_str):
	return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()


def parse_bool(b):
	if b in (True, 1, 'true', 'yes', 'on', '1'):
		return True
	elif b in (False, 0, 'false', 'no', 'off', '0'):
		return False
	raise ValueError("Not a valid boolean")


def now():
	return datetime.datetime.now().date()


@app.route("/")
def index():
	return redirect(url_for("date_show", date=now().isoformat()))


@app.route("/favicon.ico")
def favicon():
	return app.send_static_file('favicon.ico')


def fullpath(request):
	fp = request.path
	if request.query_string:
		fp += '?' + str(request.query_string, 'utf-8')
	print(fp)
	return fp


def require_user(f):
	@functools.wraps(f)
	def wrapper(*args, **kwargs):
		if 'user_id' not in session:
			return render_template('login.html', version=__version__, redirect=fullpath(request))
		else:
			g.user = User.query.filter_by(id=session['user_id']).first()
			if g.user is None:
				abort(500, "Your account doesn't exist anymore.")
			return f(*args, **kwargs)
	return wrapper


@app.route("/login", methods=['POST'])
def login():
	if not app.config['RE_USER'].match(request.form["user"]):
		abort(400, "Invalid username.")
	user = User.query.filter_by(name=request.form["user"]).first()
	if user is None:  # or not passlib.hash.bcrypt.verify(request.form["pass"], user.pass_hash):
		abort(403, "Invalid username or password")
	session['user_id'] = user.id
	return redirect(request.args.get('redirect', url_for('date_show', date=now().isoformat())))


@app.route("/logout", methods=['GET', 'POST'])
def logout():
	if 'user_id' in session:
		del session['user_id']
	return redirect(request.args.get('redirect', url_for('date_show', date=now().isoformat())))


@app.route("/terms", methods=['GET'])
def terms():
	return render_template('terms.html', version=__version__)


@app.route("/<date>/", methods=["GET"])
@require_user
def date_show(date):
	date = parse_date(date)
	if date.weekday() != 0:
		return render_template("notmonday.html", version=__version__)
	trips = Trip.query.filter_by(date=date).all()
	destinations = Destination.query.all()

	return render_template("date.html",
		**GLOBAL_PARAMS,
		user=g.user,
		date=date,
		next_date=date + datetime.timedelta(days=7),
		prev_date=date + datetime.timedelta(days=-7),
		trips=trips,
		destinations=destinations,
		msg=request.args.get("msg"),
		msg_severity=request.args.get("msg_severity"),
	)


@app.route("/<date>/", methods=["POST"])
@require_user
def date_submit_trip(date):
	destination = Destination.query.filter_by(id=request.form["destination"]).first()
	trip = Trip(user=g.user, destination=destination, date=parse_date(date))
	db.session.add(trip)
	try:
		db.session.commit()
		return redirect(url_for("date_show", date=date))
	except sqlalchemy.exc.IntegrityError:
		return redirect(url_for("date_show", date=date, msg="You've already added a trip to that destination!", msg_severity="error"))


@app.route("/trip/<int:trip_id>/order", methods=["POST"])
@require_user
def trip_submit_order(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if trip.closed:
		abort(400, "This trip is already closed.")
	for item_id, count in request.form.to_dict().items():
		if not item_id.startswith("item-"):
			continue
		item_id = item_id.replace("item-", "", 1)
		count = int(count)

		item = Item.query.filter_by(id=item_id).first()
		if item.historical and count != 0:
			abort(400, "That item is not orderable any more.")

		if count > int(app.config.get('MAX_ORDER_COUNT', 16)):
			abort(400, "You can't order that many items. You can thank the person that ordered 65535 drinks once.")
		if count < 0:
			abort(400, "You can't order a negative number of items. What does that even mean?")

		orders = Order.query.filter_by(trip=trip, item=item, user=g.user).all()
		if len(orders) > count:
			for order in orders[count:]:
				db.session.delete(order)
		elif len(orders) < count:
			for i in range(len(orders), count):
				db.session.add(Order(trip=trip, item=item, user=g.user, settled=item.price <= 0 or trip.user==g.user))
	db.session.commit()

	return redirect(url_for("date_show", date=trip.date, msg="Order accepted!", msg_severity='success'))


@app.route("/trip/<int:trip_id>/close", methods=["POST"])
@require_user
def trip_close(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if g.user != trip.user:
		abort(403, "You can't close someone else's trip.")
	trip.closed = True
	db.session.add(trip)
	db.session.commit()
	return redirect(url_for("trip_show", trip_id=trip_id))


@app.route("/trip/<int:trip_id>")
@require_user
def trip_show(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if g.user != trip.user:
		abort(403, "You can't read someone else's order list.")
	trip_items = trip.get_items_grouped()
	total = sum(o["item"].price * len(o["users"]) for o in trip_items)
	return render_template("trip.html",
		**GLOBAL_PARAMS,
		user=g.user,
		trip=trip,
		trip_items=trip_items,
		show_users="users" in request.args,
		total=total,
	)


@app.route("/settle")
@require_user
def settle_show():
	# All orders that were ordered by us, but not bought by us
	query_out = db.session.query(Order).filter(Order.user == g.user, Order.trip.has(Trip.user != g.user))
	# All orders that were not ordered by us, but were bought by us
	query_in = db.session.query(Order).filter(Order.user != g.user, Order.trip.has(Trip.user == g.user))

	filtered = False
	if 'trip' in request.args:
		query_out = query_out.filter(Order.trip_id.in_(request.args.getlist('trip')))
		query_in = query_in.filter(Order.trip_id.in_(request.args.getlist('trip')))
		filtered = True
	for after in request.args.getlist('after'):
		query_out = query_out.filter(Order.date > after)
		query_in = query_in.filter(Order.date > after)
		filtered = True
	for since in request.args.getlist('since'):
		query_out = query_out.filter(Order.date >= since)
		query_in = query_in.filter(Order.date >= since)
		filtered = True
	for before in request.args.getlist('before'):
		query_out = query_out.filter(Order.date < before)
		query_in = query_in.filter(Order.date < before)
		filtered = True
	for until in request.args.getlist('until'):
		query_out = query_out.filter(Order.date <= until)
		query_in = query_in.filter(Order.date <= until)
		filtered = True
	if 'with' in request.args:
		# for outgoing (ordered by us), check the Trip's user
		query_out = query_out.filter(Order.trip.has(Trip.user_id.in_(map(int, request.args.getlist('with')))))
		# For incoming (ordered from us), check the Order's user
		query_in = query_in.filter(Order.user_id.in_(map(int, request.args.getlist('with'))))
		filtered = True
	if 'settled' in request.args:
		filter_settled = parse_bool(request.args['settled'])
		query_out = query_out.filter(Order.settled == filter_settled)
		query_in = query_in.filter(Order.settled == filter_settled)
		filtered = True

	return render_template("settle.html",
		**GLOBAL_PARAMS,
		user=g.user,
		outgoing=query_out.all(),
		incoming=query_in.all(),
		filtered=filtered,
	)


@app.route("/settle", methods=["POST"])
@require_user
def settle_update():
	form = request.form.to_dict()
	orders_form = {}
	for key, value in form.items():
		if key.startswith("old-"):
			order_id = int(key.replace("old-", "", 1))
			orders_form[order_id] = (value == "on", form.get(f"order-{order_id}", "off") == "on")
	orders_db = db.session.query(Order).filter(Order.id.in_(orders_form)).all()
	for order in orders_db:
		old_state, new_state = orders_form[order.id]
		if new_state != old_state:
			order.settled = new_state
			db.session.add(order)
	db.session.commit()
	return redirect(url_for("settle_show"))
