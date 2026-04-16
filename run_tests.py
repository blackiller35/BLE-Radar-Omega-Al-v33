#!/usr/bin/env python3
"""Script de test pour les fonctions de validation d'adresses IP."""

import sys
sys.path.insert(0, '/home/tigars20244/Bureau/BLE-Radar-Omega-AI-v33/ble_radar')

from test import valider_ipv4, valider_ipv6, valider_ip


def test_ipv4():
    """Tests pour IPv4."""
    print("=" * 50)
    print("TESTS IPv4")
    print("=" * 50)

    tests = [
        ("192.168.1.1", True),
        ("8.8.8.8", True),
        ("10.0.0.1", True),
        ("172.16.0.1", True),
        ("0.0.0.0", True),
        ("255.255.255.255", True),
        ("256.1.1.1", False),
        ("1.256.1.1", False),
        ("999.168.1.1", False),
        ("10.0.0.256", False),
        ("192.168.1", False),
        ("192.168.1.1.1", False),
        ("192.168.1.a", False),
        ("invalid", False),
        ("2001:db8::1", False),
    ]

    passed = 0
    failed = 0
    for ip, expected in tests:
        result = valider_ipv4(ip)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: valider_ipv4('{ip}') = {result} (attendu: {expected})")

    print(f"\nRésultats IPv4: {passed} passés, {failed} échoués")
    return failed == 0


def test_ipv6():
    """Tests pour IPv6."""
    print("\n" + "=" * 50)
    print("TESTS IPv6")
    print("=" * 50)

    tests = [
        ("2001:db8::1", True),
        ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", True),
        ("::1", True),
        ("::", True),
        ("fe80::1", True),
        ("ff00::1", True),
        ("2001:db8::", True),
        ("::ffff:192.0.2.1", True),
        ("2001:DB8::1", True),
        ("2001:Db8::1", True),
        ("ABCD:EF01::1", True),
        ("gggg::1", False),
        ("2001:db8:::1", False),
        ("2001:db8::1::2", False),
        ("192.168.1.1", False),
        ("invalid", False),
        ("", False),
    ]

    passed = 0
    failed = 0
    for ip, expected in tests:
        result = valider_ipv6(ip)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: valider_ipv6('{ip}') = {result} (attendu: {expected})")

    print(f"\nRésultats IPv6: {passed} passés, {failed} échoués")
    return failed == 0


def test_mixed():
    """Tests pour IPv4 ou IPv6."""
    print("\n" + "=" * 50)
    print("TESTS IPv4 ou IPv6")
    print("=" * 50)

    tests = [
        ("192.168.1.1", True),
        ("8.8.8.8", True),
        ("127.0.0.1", True),
        ("2001:db8::1", True),
        ("::1", True),
        ("fe80::1", True),
        ("invalid", False),
        ("256.1.1.1", False),
        ("gggg::1", False),
        ("", False),
        ("192.168.1", False),
    ]

    passed = 0
    failed = 0
    for ip, expected in tests:
        result = valider_ip(ip)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status}: valider_ip('{ip}') = {result} (attendu: {expected})")

    print(f"\nRésultats IPv4/IPv6: {passed} passés, {failed} échoués")
    return failed == 0


if __name__ == "__main__":
    all_passed = True
    all_passed &= test_ipv4()
    all_passed &= test_ipv6()
    all_passed &= test_mixed()

    print("\n" + "=" * 50)
    if all_passed:
        print("✓ TOUS LES TESTS SONT PASSÉS")
        sys.exit(0)
    else:
        print("✗ CERTAINS TESTS ONT ÉCHOUÉ")
        sys.exit(1)
