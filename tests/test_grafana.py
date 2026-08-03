import json
from unittest.mock import Mock

from grafana import init as grafana_init


def test_update_datasource_references_supports_schema_v2():
    dashboard = {
        "annotations": [
            {
                "query": {
                    "datasource": {
                        "name": "-- Grafana --",
                    }
                }
            }
        ],
        "elements": {
            "panel-1": {
                "datasource": {
                    "name": "old-datasource",
                }
            }
        },
        "legacy": {
            "datasource": {
                "type": "postgres",
                "uid": "old-datasource",
            }
        },
    }

    updated = grafana_init.update_datasource_references(
        dashboard,
        "new-datasource",
    )

    assert updated == 2
    assert (
        dashboard["annotations"][0]["query"]["datasource"]
        == {"name": "-- Grafana --"}
    )
    assert dashboard["elements"]["panel-1"]["datasource"] == {
        "name": "new-datasource",
    }
    assert dashboard["legacy"]["datasource"] == {
        "type": "postgres",
        "uid": "new-datasource",
    }


def test_create_dashboard_uses_schema_v2_api(
    tmp_path,
    monkeypatch,
):
    dashboard_file = tmp_path / "dashboard.json"
    dashboard_file.write_text(
        json.dumps(
            {
                "title": "Badminton Mate Monitoring",
                "elements": {
                    "panel-1": {
                        "datasource": {
                            "name": "old-datasource",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    lookup_response = Mock(
        status_code=404,
        ok=False,
        text="not found",
    )
    create_response = Mock(
        status_code=200,
        ok=True,
        text="",
    )
    create_response.json.return_value = {
        "metadata": {
            "name": "badminton-mate-monitoring",
        }
    }

    get_mock = Mock(
        return_value=lookup_response,
    )
    post_mock = Mock(
        return_value=create_response,
    )

    monkeypatch.setattr(
        grafana_init,
        "DASHBOARD_FILE",
        dashboard_file,
    )
    monkeypatch.setattr(
        grafana_init.requests,
        "get",
        get_mock,
    )
    monkeypatch.setattr(
        grafana_init.requests,
        "post",
        post_mock,
    )

    grafana_init.create_or_update_dashboard(
        "new-datasource",
    )

    expected_collection_url = (
        f"{grafana_init.GRAFANA_URL}"
        "/apis/dashboard.grafana.app/v1"
        f"/namespaces/{grafana_init.DASHBOARD_NAMESPACE}"
        "/dashboards"
    )

    post_mock.assert_called_once()
    assert post_mock.call_args.args[0] == (
        expected_collection_url
    )

    payload = post_mock.call_args.kwargs["json"]

    assert payload["metadata"]["name"] == (
        grafana_init.DASHBOARD_RESOURCE_NAME
    )
    assert (
        payload["spec"]["elements"]["panel-1"]
        ["datasource"]["name"]
        == "new-datasource"
    )
