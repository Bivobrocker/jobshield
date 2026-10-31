
import socket
import ipaddress
from urllib.parse import urlsplit
from datetime import datetime, timezone


def check_domain(website):
    """
    Confirm public DNS resolution only.
    HTTP reachability is checked by company website discovery.
    This does not independently verify company ownership.
    """
    checked_at = datetime.now(timezone.utc).isoformat()

    if not website:
        return {
            "category": "DOMAIN_CHECK",
            "status": "MISSING",
            "severity": "INFO",
            "finding": "Company domain was not provided.",
            "source_url": None,
            "checked_at": checked_at
        }

    try:
        parsed = urlsplit(website.strip())

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid domain")

        domain = parsed.hostname.lower().rstrip(".")

        if domain == "localhost" or domain.endswith(".localhost"):
            raise ValueError("Local domain is not allowed")

        # Resolve DNS and collect IP addresses.
        try:
            ip = ipaddress.ip_address(domain)
            addresses = [str(ip)]
        except ValueError:
            addresses = list({
                result[4][0]
                for result in socket.getaddrinfo(
                    domain, None, type=socket.SOCK_STREAM
                )
            })

        if not addresses:
            raise ValueError("No DNS records found")

        # Reject private and non-public IP addresses.
        for address in addresses:
            if not ipaddress.ip_address(address).is_global:
                raise ValueError(
                    "Domain resolves to a non-public IP"
                )

        return {
            "category": "DOMAIN_CHECK",
            "status": "UNVERIFIED",
            "severity": "INFO",
            "finding": (
                "Domain DNS resolution confirmed. "
                "However, independent company-domain ownership "
                "verification is unavailable. This does not indicate "
                "fraud; manual verification is recommended."
            ),
            "source_url": website,
            "checked_at": checked_at,
            "resolved_ips": addresses
        }

    except ValueError:
        return {
            "category": "DOMAIN_CHECK",
            "status": "MISMATCH",
            "severity": "WARNING",
            "finding": (
                "Domain is invalid, unsafe, or resolves "
                "to a non-public IP."
            ),
            "source_url": website,
            "checked_at": checked_at
        }

    except (socket.gaierror, OSError):
        return {
            "category": "DOMAIN_CHECK",
            "status": "UNABLE_TO_VERIFY",
            "severity": "WARNING",
            "finding": (
                "Domain DNS resolution could not be verified."
            ),
            "source_url": website,
            "checked_at": checked_at
        }

    except Exception:
        return {
            "category": "DOMAIN_CHECK",
            "status": "UNABLE_TO_VERIFY",
            "severity": "WARNING",
            "finding": (
                "Domain verification encountered "
                "an unexpected error."
            ),
            "source_url": website,
            "checked_at": checked_at
        }
