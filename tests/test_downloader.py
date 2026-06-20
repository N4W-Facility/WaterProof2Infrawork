from core.downloader import WaterProofDownloader


def test_placeholder():
    d = WaterProofDownloader()
    assert d.base_url == "https://water-proof.org"
