# Main program entry point for nl2bash
from .llm_translator import LLMTranslator
from .history_analyzer import HistoryAnalyzer
from .utils import helper_function

def main_loop():
    """
    Main loop for the nl2bash application.
    """
    translator = LLMTranslator()
    history_analyzer = HistoryAnalyzer() # Uses default history file

    print("Welcome to NL2Bash!")
    print("Type your command in natural language, or 'exit' to quit.")

    while True:
        try:
            user_input = input("> ")
            if user_input.lower() == 'exit':
                print("Exiting NL2Bash.")
                break

            if not user_input:
                continue

            # 1. Translate NL to Bash using LLM
            llm_command = translator.translate(user_input)
            print(f"LLM Suggestion: {llm_command}")

            # 2. Get relevant history (e.g., based on the first word of the command)
            # This is a simplistic way to get a prefix for history search
            command_parts = llm_command.strip().lstrip("# ").split(" ")
            prefix_for_history = command_parts[0] if command_parts else ""

            relevant_history = []
            if prefix_for_history:
                relevant_history = history_analyzer.get_relevant_history(prefix_for_history)

            # 3. Correct command based on history
            corrected_command = history_analyzer.correct_command(llm_command, relevant_history)
            print(f"Corrected/Final Command: {corrected_command}")

            # (Optional) Execute command or show to user
            # For now, just print. In a real tool, you might offer to execute it.
            # helper_function() # Example of using a utility

        except KeyboardInterrupt:
            print("\nExiting NL2Bash (Ctrl+C).")
            break
        except EOFError:
            print("\nExiting NL2Bash (EOF).")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            # Potentially log the error or offer to retry

if __name__ == "__main__":
    main_loop()
