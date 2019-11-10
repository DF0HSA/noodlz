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

```
NOODLZ_SETTINGS=/path/to/noodlz.cfg.example FLASK_APP=noodlz:app FLASK_DEBUG=1 python3 -m flask run
```

`NOODLZ_SETTINGS` is resolved relative to `__init__.py`

## CLI

The CLI is used mostly to manage 

```
NOODLZ_SETTINGS=/path/to/noodlz.cfg python3 -m noodlz
```

`NOODLZ_SETTINGS` is resolved relative to `__main__.py`
