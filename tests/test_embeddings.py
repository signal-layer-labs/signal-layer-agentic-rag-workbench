from app.rag.embeddings import MockEmbeddingProvider


def test_mock_embeddings_are_deterministic_and_fixed_size() -> None:
    provider = MockEmbeddingProvider(dimensions=32)

    first = provider.embed_text("discount approval rules")
    second = provider.embed_text("discount approval rules")

    assert first == second
    assert len(first) == 32
    assert provider.embed_batch(["discount approval rules"]) == [first]
