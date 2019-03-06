# Noodlz

A small, simple webapp to collect orders for Developer Monday at DF0HSA.

# Running

```
NOODLZ_SETTINGS=noodlz.cfg gunicorn noodlz:app
```

To run on a different port, override the systemd service to pass extra arguments to gunicorn:

`/etc/systemd/system/noodlz.service.d/override.conf`
```
[Service]
Environment="GUNICORN_CMD_ARGS=--bind=127.0.0.1:1234"
```