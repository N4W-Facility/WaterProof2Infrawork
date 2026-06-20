from core.transformer import SpatialTransformer


def test_placeholder():
    assert SpatialTransformer() is not None
