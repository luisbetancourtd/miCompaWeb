"""M2 semantic chunker - Chonkie-like chunking para RAG."""

from typing import List
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int
    char_start: int
    char_end: int
    overlap_prev: str = ""  # últimas N chars del chunk anterior


class SemanticChunker:
    """Chunker semántico para RAG."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        split_by: str = "paragraph",  # paragraph, sentence, word
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.split_by = split_by

    def chunk(self, text: str) -> List[Chunk]:
        """Divide texto en chunks semánticos."""
        if not text:
            return []

        # Split por unidades semánticas
        if self.split_by == "paragraph":
            units = [p.strip() for p in text.split("\n\n") if p.strip()]
        elif self.split_by == "sentence":
            import re
            units = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        else:
            units = text.split()

        chunks: List[Chunk] = []
        current_text = ""
        current_start = 0

        for i, unit in enumerate(units):
            candidate = current_text + ("\n\n" if current_text else "") + unit

            if len(candidate) <= self.chunk_size:
                current_text = candidate
            else:
                # Guardar chunk anterior
                if current_text:
                    char_end = current_start + len(current_text)
                    overlap = current_text[-self.chunk_overlap:] if len(current_text) > self.chunk_overlap else ""
                    chunks.append(Chunk(
                        text=current_text,
                        index=len(chunks),
                        char_start=current_start,
                        char_end=char_end,
                        overlap_prev=overlap,
                    ))
                current_text = unit
                current_start = sum(len(c.text) + 2 for c in chunks)  # aprox

        # Último chunk
        if current_text:
            char_end = current_start + len(current_text)
            overlap = current_text[-self.chunk_overlap:] if len(current_text) > self.chunk_overlap else ""
            chunks.append(Chunk(
                text=current_text,
                index=len(chunks),
                char_start=current_start,
                char_end=char_end,
                overlap_prev=overlap,
            ))

        return chunks

    def chunk_with_overlap(self, texts: List[str]) -> List[Chunk]:
        """Chunk múltiples textos con reindexación."""
        all_chunks: List[Chunk] = []
        for text in texts:
            chunks = self.chunk(text)
            for c in chunks:
                c.index = len(all_chunks)  # reindex global
                all_chunks.append(c)
        return all_chunks
