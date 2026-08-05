"""
AI Assistant — Infor Information Development Standards Expert.

Uses local Ollama to provide an AI assistant that knows the full Infor
ID standards and helps information developers write, edit, review, and
plan product documentation.

Communication is via the OpenAI-compatible API exposed by Ollama at
http://localhost:11434/v1.
"""

import json
import logging
import os
import time
from typing import Generator

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_API_KEY = "ollama"  # Dummy key required by the SDK

# Maximum conversation history to retain (in messages)
MAX_HISTORY_MESSAGES = 10

# =============================================================================
# SYSTEM PROMPT — Infor ID Standards Knowledge Base
# =============================================================================

SYSTEM_PROMPT = """You are an Infor Information Development (ID) writing standards expert. You help writers write, edit, review, plan, and generate documentation for Infor products (LN, M3, WMS, CSI, Infor OS, IFSM, DEPM, Factory Track, Landmark, SCP, etc.).

## CAPABILITIES
Search docs, summarize help topics, rewrite for compliance, suggest topic types, create outlines/FAQs/troubleshooting/release notes, extract procedures, explain APIs, identify doc gaps, suggest metadata/keywords, compare topics across products, plan information architecture.

## WORD SUBSTITUTIONS (ALWAYS ENFORCE)
abort→cancel/stop, able to→can, activate→start, amend→change, appear→show/display, as a result→therefore, at all times→always, back-end→server/database, ballpark figure→estimate, be sure/make sure→ensure, blacklist→block list, click on→click, comprise→include/consist of, default(verb)→rewrite, desire/want/wish→can, due to→because, e.g.→for example, enter(typing)→specify, execute(program)→run, execute(action)→perform, fetch→retrieve, file name→filename, finalize→complete, grayed out→not available, hang→stop responding, hard→difficult, have to→must, hover→hover over, i.e.→that is, if you want to/in order to/to be able to→to, impact(verb)→affect, is prior to→before, it is possible→you can, kill→stop/end, like→such as, login/log on→sign in, log out→sign out, mandatory→required, master→primary, slave→secondary, minorities→underrepresented groups, native(feature)→built-in, need→require, on-line→online, populate→fill, prior to→before, proper/right→correct, since(reason)→because, submenu→menu, subsequently→then, the system requires→you must, toggle→switch, utilize→use, via→by/through, whether or not→whether, whitelist→allow list, wrong→incorrect, you must not→do not

## WORDS TO REMOVE
actually, allows, basically, below, by using, clearly, designed to, easily, following, greatly, hence, in the appropriate field, just, keep in mind, little, obviously, of course, please, quickly, quite, rather, really, simple, simply, strongly recommended, very, which means that

## GRAMMAR RULES
- Active voice for user actions; passive only for system actions
- Present tense for current actions; future only for clearly future events
- Imperative mood for instructions ("Click Save" not "You should click Save")
- Sentences ≤25 words. Paragraphs ≤5 sentences.
- No anthropomorphism (software doesn't "allow/want/think/know")
- No standalone pronouns (this/that/it) — always pair with noun
- Address reader as "you". Use "you must" for required, "you should" for recommended, "you can" for optional
- No contractions in formal docs. Use contractions (don't, can't, isn't) only for conversational UI text.
- Place field/table names BEFORE descriptor: "Customer Name field" not "field Customer Name"
- Place modifiers immediately before words they modify (especially "only")
- Limit noun clusters to 3 nouns max. Use prepositions to separate.
- No double negatives. No Latin abbreviations except etc.
- Never omit articles (a, an, the).
- Use "which" + comma for nonrestrictive clauses; "that" without comma for restrictive.

## FORMATTING
- Oxford comma required. Sentence-style caps for headings (no colons/dashes in headings).
- Lists: no "following/below" in intro. Bulleted=capitals+parallel. Numbered=gerund title.
- Tables: intro with "This table shows [topic]:" 
- No em dashes. No ellipsis. No semicolons in online content.
- No color coding alone (accessibility). Alt text required for all images.

## TOPIC TYPES
- Concept: "About [noun]" — explains what, no procedures
- Task: "[Gerund phrase]" — step-by-step, starts with verb
- Reference: "[Noun phrase]" — field descriptions, tables

## UI TEXT
Quantity=items, Amount=money, Code=alphanumeric IDs, Number=numeric IDs. No "please/simply/kindly". No colored text. Culturally neutral. No concatenated labels.

## RESPONSE RULES
- Be concise. Quick questions = 1-3 sentences.
- Cite rules when correcting: "Word Usage: execute→run"
- Produce publication-ready content, no placeholders.
- When given pasted content, analyze and improve it directly.
- Use markdown formatting.
"""


# =============================================================================
# AI ASSISTANT CLASS
# =============================================================================

class AIAssistant:
    """Manages conversation with local Ollama LLM."""

    def __init__(self):
        self.client = None
        self.conversation_history = []
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the OpenAI client pointing to local Ollama."""
        if OpenAI is None:
            logger.error("openai package not installed. AI Assistant unavailable.")
            return

        try:
            self.client = OpenAI(
                base_url=OLLAMA_BASE_URL,
                api_key=OLLAMA_API_KEY,
            )
            logger.info(f"AI Assistant initialized: model={OLLAMA_MODEL}, base_url={OLLAMA_BASE_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize AI Assistant client: {e}")
            self.client = None

    def _build_messages(self, user_message: str, context: str = "") -> list:
        """Build the messages array with system prompt, context, and history."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # If additional context (e.g., uploaded standards docs) is provided
        if context:
            messages.append({
                "role": "system",
                "content": f"Additional context provided by the user:\n\n{context}"
            })

        # Add conversation history
        messages.extend(self.conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _trim_history(self):
        """Keep conversation history within bounds."""
        if len(self.conversation_history) > MAX_HISTORY_MESSAGES:
            # Keep the most recent messages
            self.conversation_history = self.conversation_history[-MAX_HISTORY_MESSAGES:]

    def chat(self, user_message: str, context: str = "") -> dict:
        """Send a message and get a complete response.

        Args:
            user_message: The user's input text.
            context: Optional additional context (e.g., standards documents content).

        Returns:
            dict with:
            - success: bool
            - response: str (the assistant's reply)
            - error: str (if success is False)
        """
        if not self.client:
            return {
                "success": False,
                "response": "",
                "error": "AI Assistant not available. Ensure Ollama is running and the openai package is installed.",
            }

        messages = self._build_messages(user_message, context)

        try:
            start_time = time.time()
            completion = self.client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
            )

            assistant_reply = completion.choices[0].message.content or ""
            duration = int((time.time() - start_time) * 1000)
            logger.info(f"AI chat completed: duration={duration}ms, reply_len={len(assistant_reply)}")

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_reply})
            self._trim_history()

            return {
                "success": True,
                "response": assistant_reply,
                "error": "",
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"AI chat error: {error_msg}")

            # Provide helpful error messages
            if "Connection refused" in error_msg or "connection error" in error_msg.lower():
                error_msg = (
                    "Cannot connect to Ollama. Please ensure Ollama is running "
                    "(run 'ollama serve' in a terminal) and the model is pulled "
                    f"(run 'ollama pull {OLLAMA_MODEL}')."
                )
            elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                error_msg = (
                    f"Model '{OLLAMA_MODEL}' not found. Please run: ollama pull {OLLAMA_MODEL}"
                )

            return {
                "success": False,
                "response": "",
                "error": error_msg,
            }

    def chat_stream(self, user_message: str, context: str = "") -> Generator[str, None, None]:
        """Send a message and stream the response token by token.

        Args:
            user_message: The user's input text.
            context: Optional additional context.

        Yields:
            str: Each chunk of the response as it arrives.
        """
        if not self.client:
            yield json.dumps({"type": "error", "content": "AI Assistant not available."})
            return

        messages = self._build_messages(user_message, context)

        try:
            stream = self.client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
                stream=True,
            )

            full_response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield json.dumps({"type": "token", "content": token})

            # Update conversation history after complete response
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": full_response})
            self._trim_history()

            yield json.dumps({"type": "done", "content": ""})

        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg or "connection error" in error_msg.lower():
                error_msg = (
                    "Cannot connect to Ollama. Please ensure Ollama is running "
                    f"and the {OLLAMA_MODEL} model is pulled."
                )
            yield json.dumps({"type": "error", "content": error_msg})

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("AI Assistant conversation history cleared")
        return {"success": True, "message": "Conversation cleared."}

    def check_status(self) -> dict:
        """Check if Ollama is reachable and the model is available."""
        if not self.client:
            return {
                "available": False,
                "model": OLLAMA_MODEL,
                "error": "OpenAI package not installed.",
            }

        try:
            # Try listing models to verify connectivity
            models = self.client.models.list()
            model_ids = [m.id for m in models.data] if models.data else []
            model_available = any(OLLAMA_MODEL.replace(":", "-") in m or OLLAMA_MODEL in m for m in model_ids)

            return {
                "available": True,
                "model": OLLAMA_MODEL,
                "model_found": model_available,
                "available_models": model_ids[:10],  # Return first 10
            }
        except Exception as e:
            return {
                "available": False,
                "model": OLLAMA_MODEL,
                "error": str(e),
            }


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

_assistant = None


def get_assistant() -> AIAssistant:
    """Get or create the singleton AI Assistant instance."""
    global _assistant
    if _assistant is None:
        _assistant = AIAssistant()
    return _assistant


def chat(message: str, context: str = "") -> dict:
    """Send a chat message to the AI Assistant."""
    return get_assistant().chat(message, context)


def chat_stream(message: str, context: str = "") -> Generator[str, None, None]:
    """Stream a chat response from the AI Assistant."""
    return get_assistant().chat_stream(message, context)


def clear_history() -> dict:
    """Clear the conversation history."""
    return get_assistant().clear_history()


def check_status() -> dict:
    """Check AI Assistant availability."""
    return get_assistant().check_status()
