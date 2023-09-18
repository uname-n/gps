from logging import basicConfig, getLogger, FileHandler, DEBUG, INFO
basicConfig(format="(%(levelname)s) [%(name)s] %(message)s", level=DEBUG)

log = getLogger("cli")
log.addHandler(FileHandler("cli.log"))
log.setLevel(INFO)

from multiprocessing.connection import Client
from click import group

from display import get_battery

# = = = = = = = = = = = = = = = = = =

def cmd(*args):
    log.info(" ".join(args))
    try:
        client = Client(('localhost', 6420))
        try:
            client.send(" ".join(args))
            response = client.recv()
            log.info(response)
        except EOFError: pass
        finally: client.close()
    except ConnectionRefusedError: print("daemon is not running.")

# = = = = = = = = = = = = = = = = = =

@group()
def cli():pass

# = = = = = = = = = = = = = = = = = =

@cli.command()
def ping(): cmd("ping")

@cli.command()
def debug(): cmd("toggle_debug")

# = = = = = = = = = = = = = = = = = =

@cli.command()
def report(): cmd("report")

@cli.command()
def waypoint(): cmd("waypoint")

@cli.command()
def done(): cmd("done")

@cli.command()
def shutdown(): cmd("shutdown")

@cli.command()
def battery():
    print(get_battery())

# = = = = = = = = = = = = = = = = = =

@group()
def disk():pass

# = = = = = = = = = = = = = = = = = =

@disk.command()
def clean(): cmd("disk_clean")

@group()
def external():pass

@external.command()
def mount(): cmd("disk_local_mount")

@external.command()
def eject(): cmd("disk_local_eject")

@group()
def local():pass

@local.command()
def mount(): cmd("disk_local_mount")

@local.command()
def eject(): cmd("disk_local_eject")

# = = = = = = = = = = = = = = = = = =

@group()
def display():pass

@display.command()
def reset():
    from display.lcd import LCD
    LCD().reset()

# = = = = = = = = = = = = = = = = = =

disk.add_command(local)
disk.add_command(external)
cli.add_command(disk)
cli.add_command(display)

# = = = = = = = = = = = = = = = = = =

if __name__ == "__main__":
    cli()
