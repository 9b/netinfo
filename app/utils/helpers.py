import datetime


def str_now_time():
    """Get current time as a string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_time():
    """Get current time."""
    return datetime.datetime.now()


def load_time(str_time):
    """Load a string date as a normal datetime."""
    return datetime.datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S")
