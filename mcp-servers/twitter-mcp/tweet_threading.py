"""
Thread Splitting for Twitter Integration

Splits long content into multiple tweets using sentence-boundary logic.
Ensures each tweet stays within 280 characters and maintains thread numbering.
"""

import re
from dataclasses import dataclass


MAX_TWEET_LENGTH = 280
THREAD_NUMBERING_RESERVE = 10  # Reserve chars for "[NN/NN] "
HASHTAG = "#netclaw"
HASHTAG_RESERVE = len(HASHTAG) + 1  # Space + hashtag


@dataclass
class ThreadTweet:
    """A single tweet in a thread."""
    content: str
    position: int
    total: int

    @property
    def numbered_content(self) -> str:
        """Content with thread numbering prefix."""
        return f"[{self.position}/{self.total}] {self.content}"


@dataclass
class ThreadResult:
    """Result of splitting content into a thread."""
    tweets: list[ThreadTweet]
    original_content: str

    @property
    def count(self) -> int:
        """Number of tweets in the thread."""
        return len(self.tweets)

    @property
    def is_thread(self) -> bool:
        """Whether this is a multi-tweet thread."""
        return len(self.tweets) > 1


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences, preserving sentence boundaries.

    Args:
        text: The text to split

    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation followed by space or end
    # Handles: "Hello. World", "Hello! World", "Hello? World"
    # But not: "Dr. Smith" or "U.S.A."

    # Simple sentence splitter - handles most cases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def split_at_word_boundary(text: str, max_length: int) -> list[str]:
    """
    Split text at word boundaries when it exceeds max_length.

    Args:
        text: The text to split
        max_length: Maximum length per chunk

    Returns:
        List of chunks
    """
    if len(text) <= max_length:
        return [text]

    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + (1 if current_chunk else 0)  # +1 for space

        if current_length + word_length <= max_length:
            current_chunk.append(word)
            current_length += word_length
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def create_thread(content: str, include_hashtag: bool = True) -> ThreadResult:
    """
    Split content into a thread of tweets.

    Algorithm:
    1. If content fits in one tweet, return single tweet
    2. Split into sentences
    3. Greedily combine sentences up to max length
    4. If a sentence exceeds max, split at word boundary
    5. Add thread numbering to each tweet
    6. Ensure hashtag on last tweet

    Args:
        content: The full content to split
        include_hashtag: Whether to include #netclaw on last tweet

    Returns:
        ThreadResult with list of tweets
    """
    # Calculate effective max length per tweet
    # Reserve space for numbering and hashtag on last tweet
    effective_max = MAX_TWEET_LENGTH - THREAD_NUMBERING_RESERVE

    # Check if content fits in single tweet
    single_tweet_content = content
    if include_hashtag and HASHTAG.lower() not in content.lower():
        single_tweet_content = f"{content} {HASHTAG}"

    if len(single_tweet_content) <= MAX_TWEET_LENGTH:
        return ThreadResult(
            tweets=[ThreadTweet(content=single_tweet_content, position=1, total=1)],
            original_content=content
        )

    # Need to split into thread
    sentences = split_into_sentences(content)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        # Check if sentence itself exceeds max
        if len(sentence) > effective_max:
            # Flush current chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Split long sentence at word boundaries
            sentence_chunks = split_at_word_boundary(sentence, effective_max)
            chunks.extend(sentence_chunks)
            continue

        # Check if adding this sentence would exceed max
        sentence_length = len(sentence) + (1 if current_chunk else 0)  # +1 for space

        if current_length + sentence_length <= effective_max:
            current_chunk.append(sentence)
            current_length += sentence_length
        else:
            # Start new chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)

    # Flush remaining
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Ensure hashtag on last chunk
    if include_hashtag and chunks:
        last_chunk = chunks[-1]
        if HASHTAG.lower() not in last_chunk.lower():
            if len(last_chunk) + HASHTAG_RESERVE <= effective_max:
                chunks[-1] = f"{last_chunk} {HASHTAG}"
            else:
                # Need to add new chunk for hashtag
                chunks.append(HASHTAG)

    # Create ThreadTweet objects with numbering
    total = len(chunks)
    tweets = [
        ThreadTweet(content=chunk, position=i + 1, total=total)
        for i, chunk in enumerate(chunks)
    ]

    return ThreadResult(tweets=tweets, original_content=content)


def estimate_thread_count(content: str) -> int:
    """
    Estimate how many tweets a piece of content would need.

    Args:
        content: The content to estimate

    Returns:
        Estimated number of tweets
    """
    if len(content) <= MAX_TWEET_LENGTH:
        return 1

    # Rough estimate: divide by effective max per tweet
    effective_max = MAX_TWEET_LENGTH - THREAD_NUMBERING_RESERVE - HASHTAG_RESERVE
    return (len(content) // effective_max) + 1


def validate_thread(thread_result: ThreadResult) -> list[str]:
    """
    Validate that all tweets in a thread are within limits.

    Args:
        thread_result: The thread to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    for tweet in thread_result.tweets:
        numbered = tweet.numbered_content
        if len(numbered) > MAX_TWEET_LENGTH:
            errors.append(
                f"Tweet {tweet.position}/{tweet.total} exceeds 280 chars "
                f"({len(numbered)} chars): {numbered[:50]}..."
            )

    return errors
