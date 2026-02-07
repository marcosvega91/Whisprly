"""
Whisprly - Text Cleanup Module (Claude API)
Uses Claude to correct, punctuate, and adjust the tone of transcribed text.
"""

import anthropic


class TextCleaner:
    """Cleans and improves transcribed text using the Claude API."""

    SYSTEM_PROMPT = """Sei un correttore di testi dettati vocalmente in italiano.

Il tuo compito è prendere una trascrizione grezza (output di speech-to-text) e restituire
SOLO il testo corretto, senza commenti, spiegazioni o prefissi.

Regole fondamentali:
1. Restituisci ESCLUSIVAMENTE il testo corretto, nient'altro
2. PRESERVA le parole e le espressioni originali del parlante — non riscrivere, non parafrasare
3. Correggi SOLO: punteggiatura, grammatica, maiuscole/minuscole, organizzazione frasi
4. NON sostituire parole con sinonimi (es. "vediamo" non diventa "analizziamo")
5. NON cambiare il registro linguistico (se il parlante è colloquiale, resta colloquiale)
6. Se il testo dettato contiene comandi di punteggiatura espliciti
   (es. "virgola", "punto", "a capo", "due punti", "punto esclamativo",
   "punto interrogativo", "apri parentesi", "chiudi parentesi",
   "aperte virgolette", "chiuse virgolette", "trattino"),
   sostituiscili con il simbolo corrispondente
7. Mantieni i termini tecnici inglesi come sono
8. Non aggiungere informazioni non presenti nell'originale
9. Quando è presente un blocco <contesto>, il parlante sta rispondendo o reagendo a quel testo.
   In questo caso le regole 2-5 NON si applicano. Invece:
   - Componi una risposta ben strutturata e appropriata al contesto
   - Preserva l'intento e il significato di ciò che il parlante vuole comunicare
   - RISCRIVI il testo in modo chiaro e coerente: elimina riempitivi (es. "diciamo", "tipo",
     "cioè", "ecco", "praticamente", "comunque"), ripetizioni, e frasi sconnesse
   - Formatta la risposta in modo adeguato al contesto (es. se si risponde a una mail,
     struttura il testo come una risposta email; se è un messaggio breve, mantienilo conciso)
   - Applica il tono richiesto
   - Non inventare informazioni non presenti nel dettato del parlante"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def clean(
        self,
        raw_text: str,
        tone_instruction: str = "",
        extra_instructions: str = "",
        context: str = "",
    ) -> str:
        """
        Clean and improve transcribed text.

        Args:
            raw_text: Raw text from Whisper transcription
            tone_instruction: Tone of voice instruction to apply
            extra_instructions: Additional cleanup instructions
            context: Optional context text the user is responding to

        Returns:
            str: Cleaned, corrected, and punctuated text
        """
        if not raw_text.strip():
            return ""

        # Build the user message
        user_parts = []

        if context:
            user_parts.append(f"<contesto>\n{context}\n</contesto>")

        if tone_instruction:
            user_parts.append(f"<tono>\n{tone_instruction}\n</tono>")

        if extra_instructions:
            user_parts.append(f"<istruzioni_extra>\n{extra_instructions}\n</istruzioni_extra>")

        user_parts.append(f"<trascrizione_grezza>\n{raw_text}\n</trascrizione_grezza>")

        user_message = "\n\n".join(user_parts)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ],
        )

        # Extract text from response
        result = ""
        for block in response.content:
            if block.type == "text":
                result += block.text

        return result.strip()
