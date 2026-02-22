"""Tests for PubMed channel."""

from unittest.mock import patch, MagicMock
from lib.channels.pubmed import PubMedChannel


class TestPubMedChannel:
    def test_two_step_api_pipeline(self):
        # Mock esearch response
        search_resp = MagicMock()
        search_resp.json.return_value = {
            "esearchresult": {"idlist": ["111", "222"]}
        }
        search_resp.raise_for_status = MagicMock()

        # Mock esummary response
        summary_resp = MagicMock()
        summary_resp.json.return_value = {
            "result": {
                "uids": ["111", "222"],
                "111": {
                    "title": "CRISPR Gene Editing Advances",
                    "authors": [{"name": "Smith A"}, {"name": "Jones B"}],
                    "pubdate": "2026 Feb",
                    "fulljournalname": "Nature",
                },
                "222": {
                    "title": "CAR-T Cell Therapy Results",
                    "authors": [{"name": "Lee C"}],
                    "pubdate": "2026 Jan",
                    "source": "Science",
                },
            }
        }
        summary_resp.raise_for_status = MagicMock()

        with patch("lib.channels.pubmed.requests.get", side_effect=[search_resp, summary_resp]):
            ch = PubMedChannel()
            results = ch.fetch_candidates(["CRISPR", "CAR-T"], since=None)

        assert len(results) == 2
        assert results[0].url == "https://pubmed.ncbi.nlm.nih.gov/111/"
        assert results[0].source_channel == "pubmed"
        assert results[0].extra["pmid"] == "111"
        assert results[0].extra["journal"] == "Nature"
        assert results[0].extra["authors"] == ["Smith A", "Jones B"]

        assert results[1].extra["pmid"] == "222"

    def test_empty_search_results(self):
        search_resp = MagicMock()
        search_resp.json.return_value = {"esearchresult": {"idlist": []}}
        search_resp.raise_for_status = MagicMock()

        with patch("lib.channels.pubmed.requests.get", return_value=search_resp):
            ch = PubMedChannel()
            results = ch.fetch_candidates(["rare topic"], since=None)

        assert results == []

    def test_authors_capped_at_five(self):
        search_resp = MagicMock()
        search_resp.json.return_value = {"esearchresult": {"idlist": ["1"]}}
        search_resp.raise_for_status = MagicMock()

        summary_resp = MagicMock()
        summary_resp.json.return_value = {
            "result": {
                "uids": ["1"],
                "1": {
                    "title": "Big Collab Paper",
                    "authors": [{"name": f"Author{i}"} for i in range(10)],
                    "pubdate": "2026",
                    "fulljournalname": "Cell",
                },
            }
        }
        summary_resp.raise_for_status = MagicMock()

        with patch("lib.channels.pubmed.requests.get", side_effect=[search_resp, summary_resp]):
            ch = PubMedChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert len(results[0].extra["authors"]) == 5

    def test_handles_error_gracefully(self):
        with patch("lib.channels.pubmed.requests.get", side_effect=Exception("network")):
            ch = PubMedChannel()
            results = ch.fetch_candidates(["test"], since=None)

        assert results == []

    def test_since_parameter_in_search(self):
        search_resp = MagicMock()
        search_resp.json.return_value = {"esearchresult": {"idlist": []}}
        search_resp.raise_for_status = MagicMock()

        with patch("lib.channels.pubmed.requests.get", return_value=search_resp) as mock_get:
            ch = PubMedChannel()
            ch.fetch_candidates(["CRISPR"], since="2026-02-01T00:00:00+00:00")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["mindate"] == "2026/02/01"
