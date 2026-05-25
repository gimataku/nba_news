"""T-01: RSS正常取得 / T-02: フェールオーバー"""
import responses as responses_lib

from fetcher.rss import fetch_rss

URL_HR = "https://hoopsrumors.com/feed"
URL_HW = "https://hoopswire.com/feed"
URL_CW = "https://thecoldwire.com/sports/nba/feed"

SAMPLE_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>NBA Rumors</title>
    <link>https://hoopsrumors.com</link>
    <description>NBA News</description>
    <item>
      <title>Spurs Sign New Guard</title>
      <link>https://hoopsrumors.com/2026/01/spurs-sign-new-guard</link>
      <description>San Antonio Spurs signed a new player today.</description>
    </item>
  </channel>
</rss>"""

SAMPLE_HW_XML = SAMPLE_RSS_XML.replace(b"hoopsrumors.com", b"hoopswire.com")
SAMPLE_CW_XML = SAMPLE_RSS_XML.replace(b"hoopsrumors.com", b"thecoldwire.com")


@responses_lib.activate
def test_t01_rss_normal_fetch(mocker):
    """T-01: Hoops Rumors が正常にRSSを取得・パースできること"""
    mocker.patch("fetcher.rss.time.sleep")
    responses_lib.add(responses_lib.GET, URL_HR, body=SAMPLE_RSS_XML, status=200)

    entries, source, is_fallback = fetch_rss()

    assert len(entries) > 0
    assert source == "hoops_rumors"
    assert is_fallback is False


@responses_lib.activate
def test_t02_failover_case1_hoops_wire(mocker):
    """T-02 ケース1: Hoops Rumors失敗 → Hoops Wire成功"""
    mocker.patch("fetcher.rss.time.sleep")
    responses_lib.add(responses_lib.GET, URL_HR, status=503)
    responses_lib.add(responses_lib.GET, URL_HR, status=503)
    responses_lib.add(responses_lib.GET, URL_HW, body=SAMPLE_HW_XML, status=200)

    entries, source, is_fallback = fetch_rss()

    assert len(entries) > 0
    assert source == "hoops_wire"
    assert is_fallback is True


@responses_lib.activate
def test_t02_failover_case2_cold_wire(mocker):
    """T-02 ケース2: Hoops Rumors・Hoops Wire失敗 → The Cold Wire NBA成功"""
    mocker.patch("fetcher.rss.time.sleep")
    responses_lib.add(responses_lib.GET, URL_HR, status=503)
    responses_lib.add(responses_lib.GET, URL_HR, status=503)
    responses_lib.add(responses_lib.GET, URL_HW, status=503)
    responses_lib.add(responses_lib.GET, URL_HW, status=503)
    responses_lib.add(responses_lib.GET, URL_CW, body=SAMPLE_CW_XML, status=200)

    entries, source, is_fallback = fetch_rss()

    assert len(entries) > 0
    assert source == "the_cold_wire"
    assert is_fallback is True


@responses_lib.activate
def test_t02_failover_case3_all_fail(mocker):
    """T-02 ケース3: 全ソース失敗"""
    mocker.patch("fetcher.rss.time.sleep")
    for url in [URL_HR, URL_HR, URL_HW, URL_HW, URL_CW, URL_CW]:
        responses_lib.add(responses_lib.GET, url, status=503)

    entries, source, is_fallback = fetch_rss()

    assert entries == []
    assert source == ""
    assert is_fallback is True
