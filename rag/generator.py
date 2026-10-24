
import time
import os
import sys

from dotenv import load_dotenv
from groq import Groq

from src.exception import CustomException
from src.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


class Generator:

    def __init__(self, config: dict):
        self.config = config["generation"]

        api_key = os.environ.get("GROQ_API_KEY")

        if not api_key:
            logger.warning(
                "GROQ_API_KEY is not set. "
                "Generation will fail if requested."
            )

        self.client = Groq(api_key=api_key) if api_key else None

    def generate(self, query: str, retrieved_chunks: list):
        try:
            query = query.strip()

            if not query:
                return "Please enter a question."

            if self.client is None:
                raise RuntimeError(
                    "GROQ_API_KEY is not configured."
                )

            # Handle missing retrieval results
            if not retrieved_chunks:
                return (
                    "I couldn't find relevant information in the "
                    "clinic knowledge base. Please consult your "
                    "doctor or clinic reception for guidance."
                )

            # Build context from retrieved document chunks
            context_blocks = "\n\n".join(
                (
                    f"[Source: {chunk.get('source', 'Unknown')}]\n"
                    f"{chunk.get('text', '')}"
                )
                for chunk in retrieved_chunks
                if isinstance(chunk, dict) and chunk.get("text")
            )

            if not context_blocks.strip():
                return (
                    "I couldn't find usable information in the "
                    "clinic knowledge base. Please consult your "
                    "doctor or clinic reception."
                )

            # IMPORTANT: Include BOTH the context and actual question
            user_message = f"""
Clinic knowledge base context:

{context_blocks}

Patient's question:
{query}
"""

            groq_started = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.config["model"],
                max_tokens=self.config["max_tokens"],
                messages=[
                    {
                        "role": "system",
                        "content": self.config["system_prompt"]
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )

            usage = getattr(response, "usage", None)
            logger.info(
                "PERF stage=groq_api_ms duration_ms=%.2f prompt_tokens=%s completion_tokens=%s",
                (time.perf_counter() - groq_started) * 1000,
                getattr(usage, "prompt_tokens", "unavailable"),
                getattr(usage, "completion_tokens", "unavailable"),
            )
            answer = response.choices[0].message.content

            if not answer or not answer.strip():
                raise RuntimeError(
                    "Groq returned an empty response."
                )

            answer = answer.strip()

            logger.info("Answer generation completed successfully.")

            return answer

        except Exception as e:
            logger.exception("Answer generation failed")
            raise CustomException(e, sys) from e

    def generate_stream(self, query: str, retrieved_chunks: list, request_id=None):
        """Yield Groq text chunks and log first-token/full-generation latency."""
        try:
            query = query.strip()
            if not query:
                yield "Please enter a question."
                return
            if self.client is None:
                raise RuntimeError("GROQ_API_KEY is not configured.")
            if not retrieved_chunks:
                yield ("I couldn't find relevant information in the clinic knowledge base. "
                       "Please consult your doctor or clinic reception for guidance.")
                return

            context_blocks = "\n\n".join(
                f"[Source: {chunk.get('source', 'Unknown')}]\n{chunk.get('text', '')}"
                for chunk in retrieved_chunks
                if isinstance(chunk, dict) and chunk.get("text")
            )
            if not context_blocks.strip():
                yield ("I couldn't find usable information in the clinic knowledge base. "
                       "Please consult your doctor or clinic reception.")
                return

            user_message = ("Clinic knowledge base context:\n\n" + context_blocks +
                           "\n\nPatient's question:\n" + query)
            total_started = time.perf_counter()

            # Retry once only when Groq returns no text at all.
            for attempt in range(2):
                started = time.perf_counter()
                first_token_logged = False
                output_chars = 0

                stream = self.client.chat.completions.create(
                    model=self.config["model"],
                    max_tokens=self.config["max_tokens"],
                    messages=[
                        {"role": "system", "content": self.config["system_prompt"]},
                        {"role": "user", "content": user_message},
                    ],
                    stream=True,
                )

                usage_logged = False
                finish_reason = None
                try:
                    for event in stream:
                        # Capture finish reason even if the chunk has no text.
                        if event.choices:
                            for choice in event.choices:
                                reason = getattr(choice, "finish_reason", None)
                                if reason is not None:
                                    finish_reason = reason

                        # Usage may arrive in a final chunk without choices.
                        usage = getattr(event, "usage", None)
                        if usage is not None:
                            prompt_tokens = getattr(usage, "prompt_tokens", None)
                            completion_tokens = getattr(usage, "completion_tokens", None)
                            total_tokens = getattr(usage, "total_tokens", None)

                            logger.info(
                                "PERF request_id=%s stage=llm_usage "
                                "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                                request_id or "-",
                                prompt_tokens if prompt_tokens is not None else "unavailable",
                                completion_tokens if completion_tokens is not None else "unavailable",
                                total_tokens if total_tokens is not None else "unavailable",
                            )
                            usage_logged = True

                        if not event.choices:
                            continue

                        piece = event.choices[0].delta.content
                        if not piece:
                            continue

                        if not first_token_logged:
                            logger.info(
                                "PERF request_id=%s stage=groq_first_token attempt=%d duration_ms=%.2f",
                                request_id or "-", attempt + 1,
                                (time.perf_counter() - started) * 1000,
                            )
                            first_token_logged = True

                        output_chars += len(piece)
                        yield piece
                finally:
                    close_stream = getattr(stream, "close", None)
                    if callable(close_stream):
                        close_stream()

                if not usage_logged:
                    logger.info(
                        "PERF request_id=%s stage=llm_usage status=unavailable",
                        request_id or "-",
                    )

                logger.info(
                    "PERF request_id=%s stage=llm_finish_reason value=%s",
                    request_id or "-",
                    finish_reason if finish_reason is not None else "unavailable",
                )

                logger.info(
                    "PERF request_id=%s stage=groq_stream_attempt attempt=%d duration_ms=%.2f output_chars=%d",
                    request_id or "-", attempt + 1,
                    (time.perf_counter() - started) * 1000,
                    output_chars,
                )

                if output_chars > 0:
                    logger.info(
                        "PERF request_id=%s stage=groq_generation_total duration_ms=%.2f output_chars=%d",
                        request_id or "-", (time.perf_counter() - total_started) * 1000,
                        output_chars,
                    )
                    logger.info("Streaming answer generation completed successfully.")
                    return

                if attempt == 0:
                    logger.warning(
                        "Groq stream was empty; retrying once. request_id=%s", request_id or "-"
                    )
                    continue

            logger.error("Groq returned empty streams twice.")
            yield (
                "I'm unable to generate a response right now. "
                "Please try again or contact clinic reception for assistance."
            )
            return
        except Exception as e:
            logger.exception("Streaming answer generation failed")
            raise CustomException(e, sys) from e
