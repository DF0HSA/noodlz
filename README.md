# Noodlz

A small, simple webapp to collect orders for Developer Monday at DF0HSA.

# Running

```
NOODLZ_SETTINGS=noodlz.cfg gunicorn noodlz:app
```

# Debugging

```
NOODLZ_SETTINGS=../noodlz.cfg.example FLASK_APP=noodlz:app FLASK_DEBUG=1 python3 -m flask run

