import pytest
from ble_radar.ip_validation import valider_ipv4, valider_ipv6, valider_ip


class TestValidateIPv4:
    """Tests pour la validation d'adresses IPv4."""

    def test_ipv4_valid_standard(self):
        """Test des adresses IPv4 valides standard."""
        assert valider_ipv4("192.168.1.1") is True
        assert valider_ipv4("8.8.8.8") is True
        assert valider_ipv4("10.0.0.1") is True
        assert valider_ipv4("172.16.0.1") is True
        assert valider_ipv4("0.0.0.0") is True
        assert valider_ipv4("255.255.255.255") is True

    def test_ipv4_invalid_out_of_range(self):
        """Test des adresses IPv4 avec octets hors limites."""
        assert valider_ipv4("256.1.1.1") is False
        assert valider_ipv4("1.256.1.1") is False
        assert valider_ipv4("1.1.256.1") is False
        assert valider_ipv4("1.1.1.256") is False
        assert valider_ipv4("999.168.1.1") is False
        assert valider_ipv4("10.0.0.256") is False

    def test_ipv4_invalid_format(self):
        """Test des adresses IPv4 avec mauvais format."""
        assert valider_ipv4("192.168.1") is False
        assert valider_ipv4("192.168.1.1.1") is False
        assert valider_ipv4("192.168.1.a") is False
        assert valider_ipv4("192.168.-1.1") is False
        assert valider_ipv4("192.168..1") is False
        assert valider_ipv4("") is False
        assert valider_ipv4(".") is False

    def test_ipv4_invalid_strings(self):
        """Test des chaînes invalides."""
        assert valider_ipv4("invalid") is False
        assert valider_ipv4("192.168.1.1.") is False
        assert valider_ipv4(".192.168.1.1") is False
        assert valider_ipv4("2001:db8::1") is False  # IPv6

    def test_ipv4_edge_cases(self):
        """Test des cas limites."""
        assert valider_ipv4("0.0.0.0") is True
        assert valider_ipv4("255.255.255.255") is True
        assert valider_ipv4("127.0.0.1") is True  # localhost


class TestValidateIPv6:
    """Tests pour la validation d'adresses IPv6."""

    def test_ipv6_valid_standard(self):
        """Test des adresses IPv6 valides standard."""
        assert valider_ipv6("2001:db8::1") is True
        assert valider_ipv6("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True
        assert valider_ipv6("::1") is True  # localhost
        assert valider_ipv6("::") is True  # adresse zéro
        assert valider_ipv6("fe80::1") is True  # link-local
        assert valider_ipv6("ff00::1") is True  # multicast

    def test_ipv6_valid_compressed(self):
        """Test des adresses IPv6 compressées."""
        assert valider_ipv6("2001:db8::") is True
        assert valider_ipv6("::ffff:192.0.2.1") is True  # IPv4 mappé
        assert valider_ipv6("64:ff9b::192.0.2.33") is True
        assert valider_ipv6("2001:db8:85a3::8a2e:370:7334") is True

    def test_ipv6_invalid_format(self):
        """Test des adresses IPv6 avec mauvais format."""
        assert valider_ipv6("gggg::1") is False  # caractères invalides
        assert valider_ipv6("2001:db8:::1") is False  # triple colon
        assert valider_ipv6("2001:db8::1::2") is False  # double :: multiple
        assert valider_ipv6("2001:db8:0:0:0:0:0:") is False  # format incomplet
        assert valider_ipv6("") is False

    def test_ipv6_invalid_strings(self):
        """Test des chaînes invalides."""
        assert valider_ipv6("invalid") is False
        assert valider_ipv6("192.168.1.1") is False  # IPv4
        assert valider_ipv6("zzzz::1") is False
        assert valider_ipv6("192.168.1.1:8080") is False  # IPv4 avec port

    def test_ipv6_case_insensitive(self):
        """Test que les lettres majuscules et minuscules sont acceptées."""
        assert valider_ipv6("2001:DB8::1") is True
        assert valider_ipv6("2001:Db8::1") is True
        assert valider_ipv6("ABCD:EF01::1") is True


class TestValidateIP:
    """Tests pour la validation d'adresses IPv4 ou IPv6."""

    def test_ip_valid_ipv4(self):
        """Test que les IPv4 valides sont acceptées."""
        assert valider_ip("192.168.1.1") is True
        assert valider_ip("8.8.8.8") is True
        assert valider_ip("127.0.0.1") is True

    def test_ip_valid_ipv6(self):
        """Test que les IPv6 valides sont acceptées."""
        assert valider_ip("2001:db8::1") is True
        assert valider_ip("::1") is True
        assert valider_ip("fe80::1") is True

    def test_ip_invalid(self):
        """Test que les adresses invalides sont rejetées."""
        assert valider_ip("invalid") is False
        assert valider_ip("256.1.1.1") is False
        assert valider_ip("gggg::1") is False
        assert valider_ip("") is False
        assert valider_ip("192.168.1") is False

    def test_ip_mixed(self):
        """Test avec un mélange d'IPv4 et IPv6."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "2001:db8::1",
            "::1",
            "fe80::1",
        ]
        for ip in valid_ips:
            assert valider_ip(ip) is True

        invalid_ips = [
            "999.999.999.999",
            "gggg::gggg",
            "localhost",
            "example.com",
        ]
        for ip in invalid_ips:
            assert valider_ip(ip) is False
