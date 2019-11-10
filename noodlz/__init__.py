import datetime
import functools
import json
import re
import os.path

from flask import Flask
from flask import url_for, redirect, render_template, abort
from flask import session, request, g
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy.exc
import passlib.hash

__version__ = "2.0.1"


app = Flask(__name__)
app.config.from_envvar('NOODLZ_SETTINGS')
app.config['RE_USER'] = re.compile(app.config.get('RE_USER', '^[A-Za-z_][A-Za-z0-9-_]{,31}$'))
db = SQLAlchemy(app)


class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(32), unique=True, nullable=False)
	pass_hash = db.Column(db.String(128), nullable=False)


class Destination(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(128), unique=True, nullable=False)


class Item(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.Text(), unique=True, nullable=False)
	tag = db.Column(db.String(16), default=None, nullable=True)
	price = db.Column(db.Numeric(9, scale=2), nullable=False)
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


@app.route("/login/", methods=['POST'])
def login():
	if not app.cpnfig['RE_USER'].match(request.form["user"]):
		abort(400, "Invalid username.")
	user = User.query.filter_by(name=request.form["user"]).first()
	if user is None:  # or not passlib.hash.bcrypt.verify(request.form["pass"], user.pass_hash):
		abort(403, "Invalid username or password")
	session['user_id'] = user.id
	return redirect(request.args.get('redirect', url_for('date_show', date=now().isoformat())))


@app.route("/logout/", methods=['GET', 'POST'])
def logout():
	if 'user_id' in session:
		del session['user_id']
	return redirect(request.args.get('redirect', url_for('date_show', date=now().isoformat())))


@app.route("/terms/", methods=['GET'])
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
		user=g.user,
		date=date,
		trips=trips,
		destinations=destinations,
		version=__version__,
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
		item = Item.query.filter_by(id=item_id).first()

		count = int(count)
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
				db.session.add(Order(trip=trip, item=item, user=g.user, settled=item.price <= 0))
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
	return redirect(url_for("trip_show_orders", trip_id=trip_id))


@app.route("/trip/<int:trip_id>")
@require_user
def trip_show_orders(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if g.user != trip.user:
		abort(403, "You can't read someone else's order list.")
	trip_items = trip.get_items_grouped()
	total = sum(o["item"].price * len(o["users"]) for o in trip_items)
	return render_template("orders.html",
		user=g.user,
		trip=trip,
		trip_items=trip_items,
		show_users="users" in request.args,
		total=total,
	)


@app.route("/trip/<int:trip_id>/settle")
@require_user
def trip_show_settle(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if g.user != trip.user:
		abort(403, "You can't read someone else's order settlement.")
	return render_template("settle.html",
		user=g.user,
		trip=trip,
	)


@app.route("/trip/<int:trip_id>/settle", methods=["POST"])
@require_user
def trip_update_settle(trip_id):
	trip = Trip.query.filter_by(id=trip_id).first()
	if g.user != trip.user:
		abort(403, "You can't read settle someone else's bills.")
	settle = request.form.to_dict()
	for order in trip.orders:
		new_paid = settle.get(f"order-{order.id}", "off") == "on"
		if order.settled != new_paid:
			order.settled = new_paid
			db.session.add(order)
	db.session.commit()
	return redirect(url_for("trip_show_settle", trip_id=trip_id))
