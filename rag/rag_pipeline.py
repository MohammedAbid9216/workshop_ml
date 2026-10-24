import time
import sys

from src.exception import CustomException
from src.logger import get_logger

from rag.generator import Generator
from rag.retriever import Retriever
from rag.rag_config_loader import load_rag_config

logger = get_logger(__name__)


class RAGPipeline:

    def __init__(self):
        self.config = load_rag_config()
        self.retriever = Retriever(self.config)
        self.generator = Generator(self.config)

    def answer(self, query: str):
        try:
            query = query.strip()

            if not query:
                return {
                    "answer": "Please enter a question.",
                    "sources": [],
                    "retrieved_chunks": []
                }

            logger.info("RAG query received.")

            # Step 1: Retrieve relevant document chunks
            retrieval_started = time.perf_counter()
            retrieved_chunks = self.retriever.retrieve(query)
            logger.info("PERF stage=rag_retrieval_ms duration_ms=%.2f", (time.perf_counter() - retrieval_started) * 1000)

            # Step 2: Handle None or empty retrieval results
            if retrieved_chunks is None:
                logger.warning(
                    "Retriever returned None. Using empty context."
                )
                retrieved_chunks = []

            # Ensure the retriever returns a list
            if not isinstance(retrieved_chunks, list):
                raise TypeError(
                    "Retriever must return a list of chunks, "
                    f"but received {type(retrieved_chunks).__name__}."
                )

            # Step 3: Generate the answer
            generation_started = time.perf_counter()
            answer_text = self.generator.generate(
                query,
                retrieved_chunks
            )
            logger.info("PERF stage=rag_generation_total_ms duration_ms=%.2f", (time.perf_counter() - generation_started) * 1000)

            # Step 4: Collect source names safely
            sources = sorted({
                chunk["source"]
                for chunk in retrieved_chunks
                if isinstance(chunk, dict)
                and chunk.get("source")
            })

            # Step 5: Build the response
            response = {
                "answer": answer_text,
                "sources": sources,
                "retrieved_chunks": retrieved_chunks
            }

            logger.info(
                f"RAG answer generated. Sources: {sources}"
            )

            return response

        except Exception as e:
            logger.exception("RAG pipeline failed")
            raise CustomException(e, sys) from e