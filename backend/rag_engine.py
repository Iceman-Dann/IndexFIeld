from typing import List, Tuple, Optional
import ollama
from dataclasses import dataclass
import google.generativeai as genai
from openai import OpenAI
import anthropic
from .config import settings

from .document_skeleton import SkeletonExtractor, get_relevant_context
from .tribal_vault import check_unsafe_notes

@dataclass
class SourceCitation:
    text: str
    page_number: int
    chunk_index: int
    manual_id: str
    manual_name: str
    score: float

class RAGEngine:
    """Retrieval-Augmented Generation engine using Gemini 1.5 Flash with document skeletons."""
    
    SYSTEM_PROMPT = """You are IndexField AI, an intelligent assistant for industrial maintenance, operations, and general technical support.
    
    When technical documentation is provided, use it for precise answers. When no documentation is available, act as a helpful technical assistant.
    
    Rules:
    1. If technical context is provided, prioritize it for accurate, specific answers
    2. If no technical context is available, provide helpful general technical assistance
    3. Be conversational, helpful, and professional
    4. For industrial topics, provide practical, actionable advice
    5. If you don't know something, admit it and suggest where to find information
    6. Remember previous context in our conversation"""
    
    def __init__(self, skeleton_extractor: SkeletonExtractor, model: str = None):
        self.skeleton_extractor = skeleton_extractor
        self.gemini_model = None
        self.ollama_model = model or settings.OLLAMA_MODEL
        self.conversation_history = []  # Store conversation context
        self.pasted_context = ""  # Store pasted content for reference
        self.groq_client = None
        self.anthropic_client = None
        
        # Initialize Anthropic if API key is available
        if settings.ANTHROPIC_API_KEY:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                print(f"[OK] Anthropic Claude initialized ({settings.ANTHROPIC_MODEL})")
            except Exception as e:
                print(f"[ERROR] Anthropic initialization failed: {e}")
        
        
        # Initialize Groq if API key is available
        if settings.GROQ_API_KEY:
            try:
                self.groq_client = OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=settings.GROQ_API_KEY
                )
                print(f"[OK] Groq initialized ({settings.GROQ_MODEL})")
            except Exception as e:
                print(f"[ERROR] Groq initialization failed: {e}")
        
        # Initialize Gemini if API key is available
        self.gemini_models = []
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                
                # Define waterfall strategy based on quota
                # 1. Highest quota (500 RPD)
                # 2. Gemma (14.4k RPD)
                # 3. Legacy/Lower quota
                fallback_models = [
                    settings.GEMINI_MODEL,
                    "gemma-3-27b",
                    settings.GEMINI_FALLBACK_MODEL,
                    "gemini-2.5-flash"
                ]
                
                for model_name in fallback_models:
                    self.gemini_models.append((model_name, genai.GenerativeModel(model_name)))
                
                self.gemini_model = self.gemini_models[0][1] # Set primary for backwards compat
                print(f"[OK] Gemini initialized with {len(self.gemini_models)} fallback models")
            except Exception as e:
                print(f"[ERROR] Gemini initialization failed: {e}")
        
        # Also check Ollama as fallback
        self._check_ollama()
    
    def _check_ollama(self):
        """Verify Ollama is available as fallback."""
        try:
            ollama.list()
            print(f"[OK] Ollama fallback available ({self.ollama_model})")
        except Exception as e:
            print(f"[WARN] Ollama not available: {e}")
    
    def _generate_with_gemini(self, prompt: str) -> str:
        """Generate response using Gemini with automatic fallback on quota limits."""
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
        
        last_error = None
        for model_name, model in self.gemini_models:
            try:
                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=500
                    )
                )
                print(f"[GEMINI] Success using model {model_name}")
                return response.text
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "exhausted" in err_msg:
                    print(f"[GEMINI WARN] Quota exhausted for {model_name}, trying next model...")
                    last_error = e
                    continue
                else:
                    print(f"[GEMINI ERROR] {type(e).__name__} on {model_name}: {e}")
                    last_error = e
                    # For non-quota errors, we might still want to try the next model just in case
                    continue
        
        raise Exception(f"All Gemini models failed. Last error: {last_error}")
    
    def _generate_with_ollama(self, prompt: str) -> str:
        """Generate response using Ollama as fallback."""
        response = ollama.chat(
            model=self.ollama_model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.1,
                "num_predict": 500
            }
        )
        return response['message']['content'].strip()
    
    def _generate_with_groq(self, prompt: str) -> str:
        """Generate response using Groq."""
        response = self.groq_client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    def _generate_with_anthropic(self, prompt: str) -> str:
        """Generate response using Anthropic Claude."""
        response = self.anthropic_client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=500,
            temperature=0.1,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()
    
    
    def _generate(self, prompt: str) -> str:
        """Generate response using available LLM (Gemini preferred)."""
        # Try Gemini first if available
        if self.gemini_model:
            try:
                return self._generate_with_gemini(prompt)
            except Exception as e:
                print(f"Gemini generation failed, trying Anthropic: {e}")
        
        # Try Anthropic as second choice
        if self.anthropic_client:
            try:
                return self._generate_with_anthropic(prompt)
            except Exception as e:
                print(f"Anthropic generation failed, trying Groq: {e}")
        
        # Try Groq as third choice
        if self.groq_client:
            try:
                return self._generate_with_groq(prompt)
            except Exception as e:
                print(f"Groq generation failed, falling back to Ollama: {e}")
        
        # Fallback to Ollama
        try:
            return self._generate_with_ollama(prompt)
        except Exception as e:
            raise Exception(f"All LLM options failed. Gemini: {self.gemini_model is not None}, Ollama error: {e}")
    
    def query(self, query_text: str, manual_id: str = None, top_k: int = 3) -> Tuple[str, List[SourceCitation]]:
        """
        Execute RAG query using document skeletons for fast retrieval.
        
        Returns:
            Tuple of (generated_answer, list_of_sources)
        """
        # 1. Get relevant context from skeletons
        context = ""
        sources = []
        
        if manual_id and manual_id in self.skeleton_extractor.skeletons:
            context = get_relevant_context(manual_id, query_text)
            skeleton = self.skeleton_extractor.skeletons[manual_id]
            
            # Build sources from relevant sections
            for section in skeleton.sections[:top_k]:
                sources.append(SourceCitation(
                    text=section.get('summary', ''),
                    page_number=section['page'],
                    chunk_index=section.get('index', 0),
                    manual_id=manual_id,
                    manual_name=skeleton.manual_name,
                    score=section.get('confidence', 0.8)
                ))
        else:
            # Search all manuals
            for mid, skeleton in self.skeleton_extractor.skeletons.items():
                ctx = get_relevant_context(mid, query_text)
                if ctx:
                    context += f"\n\n=== {skeleton.manual_name} ===\n{ctx}"
                    for section in skeleton.sections[:2]:
                        sources.append(SourceCitation(
                            text=section.get('summary', ''),
                            page_number=section['page'],
                            chunk_index=section.get('index', 0),
                            manual_id=mid,
                            manual_name=skeleton.manual_name,
                            score=section.get('confidence', 0.8)
                        ))
        
        if not context:
            # Handle general chat when no manuals are available
            return self._handle_general_chat(query_text), []
        
        # 2. Build prompt with skeleton context
        prompt = f"""You are IndexField AI, a strict, industrial-grade technical assistant. 

CRITICAL SAFETY DIRECTIVE:
You must answer the user's question using **ONLY** the provided technical context. 
If the provided context does NOT contain the answer, you must state exactly: "The provided documentation does not contain information to answer this query."
DO NOT guess, assume, or use outside knowledge. Hallucinations in this environment can cause physical harm or equipment damage.

Context from technical manuals:
{context}

User Question: {query_text}

Provide a brief, direct answer (2-4 sentences max). Include specific numbers, torque values, and specifications ONLY if they appear in the context above.

Answer:"""
        
        # 3. Generate with LLM (Gemini preferred, Ollama fallback)
        try:
            answer = self._generate(prompt)
        except Exception as e:
            print(f"[RAG ERROR] LLM generation failed: {e}")
            
            # Smart fallback: synthesize a response from the context snippets
            doc_name = sources[0].manual_name if sources else "technical documentation"
            
            # Group by page to make it more readable
            page_data = {}
            for s in sources:
                if s.page_number not in page_data:
                    page_data[s.page_number] = []
                page_data[s.page_number].append(s.text[:200].strip())
            
            answer_parts = [f"I found the following information in **{doc_name}** regarding your query:"]
            
            for page, snippets in page_data.items():
                answer_parts.append(f"\n**Page {page}:**")
                for snippet in snippets:
                    answer_parts.append(f"- {snippet}...")
            
            answer_parts.append(f"\n\n*Note: The AI reasoning engine is currently unavailable (Error: {str(e)}). I've provided the direct source snippets above.*")
            answer = "\n".join(answer_parts)
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": query_text})
        self.conversation_history.append({"role": "assistant", "content": answer})
        
        # Keep only last 10 exchanges to prevent context overflow
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return answer, sources
    
    def _handle_general_chat(self, query_text: str) -> str:
        """Handle general chat queries when no technical documentation is available."""
        # Build conversation context
        conversation_context = ""
        if self.conversation_history:
            recent_history = self.conversation_history[-6:]  # Last 3 exchanges
            for msg in recent_history:
                conversation_context += f"{msg['role']}: {msg['content']}\n"
        
        # Include pasted context if available
        context_info = ""
        if self.pasted_context:
            context_info = f"\nPrevious context provided by user: {self.pasted_context[:200]}...\n"
        
        prompt = f"""You are IndexField AI, a helpful technical assistant. No specific technical documentation is available, so provide helpful general assistance.

{conversation_context}

{context_info}

Current question: {query_text}

Provide a helpful, conversational response. If this is a technical question, give practical advice. If you need more specific information, suggest what the user should provide."""
        
        try:
            return self._generate(prompt)
        except Exception as e:
            print(f"General chat failed: {e}")
            return f"I'm here to help with your technical questions! Could you provide more details about what you're working on? For specific equipment questions, you can upload a manual or paste relevant documentation."
    
    def query_with_context(self, query_text: str, context: str) -> Tuple[str, List[SourceCitation]]:
        """Query using user-provided pasted text as context."""
        # Store the pasted context for reference
        self.pasted_context = context
        
        # Build prompt with pasted context
        prompt = f"""The user has provided the following technical content for analysis:

--- PASTED CONTENT ---
{context[:8000]}  # Limit to prevent token overflow
--- END CONTENT ---

User Question: {query_text}

Based ONLY on the pasted content above, provide a direct, technical answer. If the answer isn't in the content, say so clearly.

Answer:"""
        
        try:
            answer = self._generate(prompt)
        except Exception as e:
            print(f"LLM generation failed for pasted context: {e}")
            answer = (
                f"Based on the content you provided:\n\n" +
                f"• Content analyzed: {len(context)} characters\n" +
                f"• Key excerpt: {context[:200]}...\n\n" +
                "Note: LLM generation failed, but I can see the content you pasted."
            )
        
        # Create a dummy source for pasted content
        sources = [SourceCitation(
            text=context[:200] + "...",
            page_number=1,
            chunk_index=0,
            manual_id="pasted_content",
            manual_name="User Pasted Content",
            score=1.0
        )]
        
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": f"[Context provided]: {context[:100]}..."})
        self.conversation_history.append({"role": "user", "content": query_text})
        self.conversation_history.append({"role": "assistant", "content": answer})
        
        # Keep only last 10 exchanges
        if len(self.conversation_history) > 30:
            self.conversation_history = self.conversation_history[-30:]
        
        return answer, sources

    def _generate_with_gemini_stream(self, prompt: str):
        """Generate response using Gemini with streaming."""
        full_prompt = f"{self.SYSTEM_PROMPT}\\n\\n{prompt}"
        
        last_error = None
        for model_name, model in self.gemini_models:
            try:
                response = model.generate_content(
                    full_prompt,
                    stream=True,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=500
                    )
                )
                for chunk in response:
                    yield chunk.text
                return
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "exhausted" in err_msg:
                    print(f"[GEMINI WARN] Quota exhausted for {model_name}, trying next model...")
                    last_error = e
                    continue
                else:
                    print(f"[GEMINI ERROR] {type(e).__name__} on {model_name}: {e}")
                    last_error = e
                    continue
        
        raise Exception(f"All Gemini models failed. Last error: {last_error}")

    async def query_stream(self, query_text: str, manual_id: str = None, top_k: int = 3):
        """Execute RAG query and yield SSE events."""
        import json
        import asyncio
        
        context = ""
        sources = []
        
        if manual_id and manual_id in self.skeleton_extractor.skeletons:
            context = get_relevant_context(manual_id, query_text)
            skeleton = self.skeleton_extractor.skeletons[manual_id]
            
            for section in skeleton.sections[:top_k]:
                sources.append({
                    "page": section['page'],
                    "source": skeleton.manual_name
                })
        else:
            for mid, skeleton in self.skeleton_extractor.skeletons.items():
                ctx = get_relevant_context(mid, query_text)
                if ctx:
                    context += f"\\n\\n=== {skeleton.manual_name} ===\\n{ctx}"
                    for section in skeleton.sections[:2]:
                        sources.append({
                            "page": section['page'],
                            "source": skeleton.manual_name
                        })
        
        # --- SAFETY TRIPWIRE ---
        if manual_id:
            pages = [s['page'] for s in sources]
            unsafe_hits = check_unsafe_notes(manual_id, pages)
            if unsafe_hits:
                warning = f"***STRICT SAFETY ALERT***: This procedure has been flagged as **UNSAFE** by Engineering (Page {unsafe_hits[0]['page']}). DO NOT proceed with the captured field notes. Contact your supervisor for the official OEM alternative.\\n\\n"
                yield f"data: {json.dumps({'token': warning})}\\\\n\\\\n"
                # We still allow the AI to answer but with the prominent warning at the top
        
        if not context:
            answer = self._handle_general_chat(query_text)
            yield f"data: {json.dumps({'token': answer})}\\n\\n"
            yield f"data: {json.dumps({'citations': []})}\\n\\n"
            return
            
        prompt = f"""You are IndexField AI, a strict, industrial-grade technical assistant. 

CRITICAL SAFETY DIRECTIVE:
You must answer the user's question using **ONLY** the provided technical context. 
If the provided context does NOT contain the answer, you must state exactly: "The provided documentation does not contain information to answer this query."
DO NOT guess, assume, or use outside knowledge. Hallucinations in this environment can cause physical harm or equipment damage.

Context from technical manuals:
{context}

User Question: {query_text}

Provide a brief, direct answer (2-4 sentences max). Include specific numbers, torque values, and specifications ONLY if they appear in the context above.

Answer:"""

        full_answer = ""
        try:
            if self.gemini_model:
                for chunk_text in self._generate_with_gemini_stream(prompt):
                    full_answer += chunk_text
                    yield f"data: {json.dumps({'token': chunk_text})}\\n\\n"
                    await asyncio.sleep(0.01)
            else:
                answer = self._generate(prompt)
                full_answer = answer
                yield f"data: {json.dumps({'token': answer})}\\n\\n"
        except Exception as e:
            print(f"[RAG ERROR] Stream failed: {e}")
            answer = f"*Note: The AI reasoning engine is currently unavailable. Error: {str(e)}*"
            full_answer = answer
            yield f"data: {json.dumps({'token': answer})}\\n\\n"
            
        unique_citations = []
        seen = set()
        for s in sources:
            key = f"{s['source']}_{s['page']}"
            if key not in seen:
                seen.add(key)
                s["type"] = "OEM"
                # Mock tribal knowledge detection based on user query for demonstration
                if "torque" in query_text.lower() and len(unique_citations) == 0:
                    s["type"] = "TRIBAL_KNOWLEDGE"
                    s["author"] = "Dave, '08"
                unique_citations.append(s)
                
        yield f"data: {json.dumps({'citations': unique_citations})}\\n\\n"
        
        self.conversation_history.append({"role": "user", "content": query_text})
        self.conversation_history.append({"role": "assistant", "content": full_answer})
    
    def check_llm_status(self) -> dict:
        """Check LLM status (Gemini primary, Ollama fallback)."""
        status = {
            "primary": "gemini",
            "gemini_available": False,
            "gemini_model": settings.GEMINI_MODEL,
            "ollama_running": False,
            "ollama_model": self.ollama_model,
            "active_provider": None
        }
        
        # Check Gemini
        if self.gemini_model:
            # Passive check: Just verify the key is present and not the default placeholder
            if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10:
                status["gemini_available"] = True
                status["active_provider"] = "gemini"
            else:
                status["gemini_error"] = "API Key missing or invalid"
        
        # Check Groq
        status["groq_available"] = False
        if self.groq_client:
            if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 10:
                status["groq_available"] = True
                if not status["active_provider"]:
                    status["active_provider"] = "groq"
        
        # Check Anthropic
        status["anthropic_available"] = False
        if self.anthropic_client:
            if settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY) > 10:
                status["anthropic_available"] = True
                if not status["active_provider"]:
                    status["active_provider"] = "anthropic"
        
        
        # Check Ollama fallback
        try:
            models = ollama.list()
            ollama_available = any(m['model'] == self.ollama_model or m['model'].startswith(self.ollama_model)
                          for m in models.get('models', []))
            status["ollama_running"] = True
            status["ollama_model_available"] = ollama_available
            if not status["active_provider"] and ollama_available:
                status["active_provider"] = "ollama"
        except Exception as e:
            status["ollama_error"] = str(e)
        
        return status
    
    # Backward compatibility
    def check_ollama_status(self) -> dict:
        """Legacy method - now checks full LLM status."""
        return self.check_llm_status()
