# llm_connector.py
class LLMConnector:
    def get_llm_response(
            self, 
            user_prompt: str = "", 
            context_prompt: str = "", 
            modelID: str = "gpt-4o-mini-2024-07-18",  
            temperature: float = 0.0
    ) -> str:
        # Pour les tests, vous pouvez même ajouter un peu de variabilité
        responses = [
            f"CECI EST UNE RÉPONSE DE L'IA. Votre question était: '{user_prompt}'",
            f"Réponse de test de l'IA. Contexte reçu: {len(context_prompt)} caractères.",
            "L'IA analyse vos données LCR... (réponse de test)",
            f"Test: Je vois que vous utilisez le modèle {modelID} avec température {temperature}"
        ]
        import random
        return random.choice(responses)

if __name__ == "__main__":
    llm_connector = LLMConnector()
    print(llm_connector.get_llm_response("Test question", "Test context"))