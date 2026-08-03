import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
DASHBOARD_FILE = Path(__file__).resolve().parent / "dashboard.json"

load_dotenv(ENV_FILE)


GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "courtmate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "courtmate")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "courtmate")

DATASOURCE_NAME = "CourtMate PostgreSQL"


def check_response(response: requests.Response, action: str) -> None:
    """Raise a readable error when a Grafana API request fails."""
    if response.ok:
        return

    raise RuntimeError(
        f"{action} failed.\n"
        f"Status code: {response.status_code}\n"
        f"Response: {response.text}"
    )


def wait_for_grafana(max_attempts: int = 30, delay: int = 2) -> None:
    """Wait until Grafana is ready to accept API requests."""
    health_url = f"{GRAFANA_URL}/api/health"

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(health_url, timeout=5)

            if response.ok:
                print("Grafana is ready.")
                return

        except requests.RequestException:
            pass

        print(f"Waiting for Grafana... ({attempt}/{max_attempts})")
        time.sleep(delay)

    raise RuntimeError(
        f"Grafana did not become ready at {GRAFANA_URL}. "
        "Make sure the Grafana container is running."
    )


def create_or_update_datasource() -> str:
    """Create the PostgreSQL datasource or update it when it already exists."""
    auth = (GRAFANA_USER, GRAFANA_PASSWORD)
    headers = {"Content-Type": "application/json"}

    datasource_payload = {
        "name": DATASOURCE_NAME,
        "type": "postgres",
        "access": "proxy",
        "url": f"{POSTGRES_HOST}:{POSTGRES_PORT}",
        "user": POSTGRES_USER,
        "database": POSTGRES_DB,
        "basicAuth": False,
        "isDefault": True,
        "jsonData": {
            "sslmode": "disable",
            "postgresVersion": 1600,
            "timescaledb": False,
        },
        "secureJsonData": {
            "password": POSTGRES_PASSWORD,
        },
    }

    print("\nPostgreSQL datasource configuration:")
    print(f"  Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"  Database: {POSTGRES_DB}")
    print(f"  User: {POSTGRES_USER}")
    print("  Password: [hidden]")

    lookup_response = requests.get(
        f"{GRAFANA_URL}/api/datasources/name/{DATASOURCE_NAME}",
        auth=auth,
        timeout=10,
    )

    if lookup_response.status_code == 200:
        existing_datasource = lookup_response.json()
        datasource_id = existing_datasource["id"]

        print(f"Updating existing datasource: {DATASOURCE_NAME}")

        response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{datasource_id}",
            auth=auth,
            headers=headers,
            json=datasource_payload,
            timeout=10,
        )
    elif lookup_response.status_code == 404:
        print(f"Creating datasource: {DATASOURCE_NAME}")

        response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            auth=auth,
            headers=headers,
            json=datasource_payload,
            timeout=10,
        )
    else:
        check_response(lookup_response, "Datasource lookup")
        raise RuntimeError("Unexpected datasource lookup result")

    check_response(response, "Datasource creation or update")

    # Retrieve the saved datasource again to obtain its UID reliably
    saved_response = requests.get(
        f"{GRAFANA_URL}/api/datasources/name/{DATASOURCE_NAME}",
        auth=auth,
        timeout=10,
    )
    check_response(saved_response, "Datasource UID retrieval")

    datasource_uid = saved_response.json()["uid"]

    print("Datasource created or updated successfully.")
    print(f"Datasource UID: {datasource_uid}")

    return datasource_uid


def update_datasource_references(
    value: object,
    datasource_uid: str,
) -> int:
    """
    Recursively replace PostgreSQL datasource UIDs throughout dashboard JSON.

    This covers panels, targets, variables and nested rows.
    """
    updated = 0

    if isinstance(value, dict):
        datasource = value.get("datasource")

        if (
            isinstance(datasource, dict)
            and datasource.get("name") != "-- Grafana --"
        ):
            datasource["name"] = datasource_uid
            datasource["uid"] = datasource_uid
            datasource["type"] = "postgres"
            updated += 1

        for child in value.values():
            updated += update_datasource_references(
                child,
                datasource_uid,
            )

    elif isinstance(value, list):
        for child in value:
            updated += update_datasource_references(
                child,
                datasource_uid,
            )

    return updated


def create_or_update_dashboard(datasource_uid: str) -> None:
    """Load dashboard.json and import it into Grafana."""
    if not DASHBOARD_FILE.exists():
        raise FileNotFoundError(
            f"Dashboard file was not found: {DASHBOARD_FILE}"
        )

    with DASHBOARD_FILE.open("r", encoding="utf-8") as file:
        dashboard_json = json.load(file)

    print(f"\nLoaded dashboard file: {DASHBOARD_FILE}")

    references_updated = update_datasource_references(
        dashboard_json,
        datasource_uid,
    )

    print(
        f"Updated {references_updated} datasource reference(s) "
        "in dashboard.json."
    )

    # Remove metadata from an exported dashboard before importing it
    dashboard_json.pop("id", None)
    dashboard_json.pop("uid", None)
    dashboard_json.pop("version", None)

    dashboard_payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "message": "Initialized by grafana/init.py",
    }

    response = requests.post(
        f"{GRAFANA_URL}/api/dashboards/db",
        auth=(GRAFANA_USER, GRAFANA_PASSWORD),
        headers={"Content-Type": "application/json"},
        json=dashboard_payload,
        timeout=20,
    )

    check_response(response, "Dashboard import")

    response_data = response.json()

    print("Dashboard imported successfully.")
    print(f"Dashboard UID: {response_data.get('uid')}")
    print(f"Dashboard URL: {GRAFANA_URL}{response_data.get('url', '')}")


def main() -> None:
    print("Starting CourtMate Grafana initialization...")
    print(f"Grafana URL: {GRAFANA_URL}")

    required_values = {
        "GRAFANA_ADMIN_USER": GRAFANA_USER,
        "GRAFANA_ADMIN_PASSWORD": GRAFANA_PASSWORD,
        "POSTGRES_HOST": POSTGRES_HOST,
        "POSTGRES_PORT": POSTGRES_PORT,
        "POSTGRES_DB": POSTGRES_DB,
        "POSTGRES_USER": POSTGRES_USER,
        "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
    }

    missing_values = [
        name for name, value in required_values.items() if not value
    ]

    if missing_values:
        raise RuntimeError(
            "Missing environment variables: "
            + ", ".join(missing_values)
        )

    wait_for_grafana()
    datasource_uid = create_or_update_datasource()
    create_or_update_dashboard(datasource_uid)

    print("\nGrafana initialization completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        requests.RequestException,
        RuntimeError,
    ) as error:
        print(f"\nGrafana initialization failed:\n{error}")
        raise SystemExit(1)