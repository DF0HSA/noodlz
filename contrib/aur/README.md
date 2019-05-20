# Build a Package

In this directory, run

```
makepkg
```

Install the resulting package with

```
pacman -U noodlz-*-any.pkg.tar.xz
```

# Run after Installation

First, add some destinations to `/var/lib/noodlz/destinations.json`.
See [the example file](../../destinations.json.example) for format.

```
systemctl start noodlz
```

The app will run on the gunicorn default port (probably 5000).
To run on a different port, override the systemd service to pass extra arguments to gunicorn:

`/etc/systemd/system/noodlz.service.d/override.conf`
```
[Service]
Environment="GUNICORN_CMD_ARGS=--bind=127.0.0.1:1234"
```
