import re
import ipaddress


def valider_ipv4(ip):
    """Valide une adresse IPv4."""
    pattern = re.compile(r"^((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$")
    return bool(pattern.match(ip))


def valider_ipv6(ip):
    """Valide une adresse IPv6."""
    try:
        ipaddress.IPv6Address(ip)
        return True
    except (ipaddress.AddressValueError, ValueError):
        return False


def valider_ip(ip):
    """Valide une adresse IPv4 ou IPv6."""
    return valider_ipv4(ip) or valider_ipv6(ip)


# Tests de validation
if __name__ == "__main__":
    print("=== Tests IPv4 ===")
    print(valider_ipv4("192.168.1.1"))   # True
    print(valider_ipv4("999.168.1.1"))   # False
    print(valider_ipv4("8.8.8.8"))       # True
    print(valider_ipv4("10.0.0.256"))    # False

    print("\n=== Tests IPv6 ===")
    print(valider_ipv6("2001:db8::1"))   # True
    print(valider_ipv6("::1"))           # True
    print(valider_ipv6("fe80::1"))       # True
    print(valider_ipv6("gggg::1"))       # False
    print(valider_ipv6("192.168.1.1"))   # False

    print("\n=== Tests IPv4 ou IPv6 ===")
    print(valider_ip("192.168.1.1"))     # True
    print(valider_ip("2001:db8::1"))     # True
    print(valider_ip("invalid"))         # False
