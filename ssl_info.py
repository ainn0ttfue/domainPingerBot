import socket
import ssl
import datetime

domains_url = [
    "devnote.in",
    "devnote_wrong.in",
    "stackoverflow.com",
    "stackoverflow.com/status/404"
]


def ssl_expiry_datetime(hostname):
    ssl_dateformat = r'%b %d %H:%M:%S %Y %Z'

    context = ssl.create_default_context()
    context.check_hostname = False

    conn = context.wrap_socket(
        socket.socket(socket.AF_INET),
        server_hostname=hostname,
    )
    # 5 second timeout
    conn.settimeout(5.0)

    conn.connect((hostname, 443))
    ssl_info = conn.getpeercert()
    # Python datetime object
    return datetime.datetime.strptime(ssl_info['notAfter'], ssl_dateformat)


if __name__ == "__main__":
    for value in domains_url:
        now = datetime.datetime.now()
        try:
            expire = ssl_expiry_datetime(value)
            diff = expire - now
            print(f"Domain name: {value} Expiry Date: {expire.strftime('%Y-%m-%d')} Expiry Day: {diff.days}")
        except Exception as e:
            print(e)
