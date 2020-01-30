# Noodlz

A small, simple webapp to collect orders for Developer Monday at DF0HSA.

## Webapp

# Running (Production)

Using the `gunicorn` http server package, and assuming `noodlz` is installed 

```
NOODLZ_SETTINGS=/path/to/noodlz.cfg gunicorn noodlz:app
```

`NOODLZ_SETTINGS` is resolved relative to `__init__.py`

# Running (Debugging)

First, create a sample database with test data, then run the app in debug mode:

```
NOODLZ_SETTINGS=../noodlz.cfg.example python -m noodlz createdb --testdata
NOODLZ_SETTINGS=../noodlz.cfg.example FLASK_APP=noodlz:app FLASK_DEBUG=1 python3 -m flask run
```

The testdata includes users `Alice`, `Bob`, `Carol` and `Dave`, all with password `password`.
There are some trips and orders on [`1970-01-05`](http://127.0.0.1:5000/1970-01-05/), [`1970-01-12`](http://127.0.0.1:5000/1970-01-12/), and [`1970-01-19`](http://127.0.0.1:5000/1970-01-19/)

## CLI

The CLI is used mostly to manage 

```
NOODLZ_SETTINGS=/path/to/noodlz.cfg python3 -m noodlz
```

`NOODLZ_SETTINGS` is resolved relative to `__main__.py`
