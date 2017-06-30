import time


def get_datetime_from_timestamp(timestamp):
    return time.strftime("%c", time.localtime(timestamp))
