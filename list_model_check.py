import os
import google.generativeai as genai

def main():
    print("=== GIT SAGE: GEMINI MODEL CHECKER ===\n")

    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("⚠️  GEMINI_API_KEY can't be found.")
        api_key = input("👉 INPUT KEY: ").strip()

    if not api_key:
        print("❌ Error: API KEY MUST BE FILLED.")
        return
    try:
        genai.configure(api_key=api_key)
        
        print("\n🔄 Loading model list...\n")
        
        # Header Tabel
        print(f"{'ID MODEL':<25} | {'NAME':<30} | {'TOKEN INPUT'}")
        print("-" * 75)

        found = False
        for m in genai.list_models():
            
            if 'generateContent' in m.supported_generation_methods:
                # remove prefix 'models/' for neat
                model_id = m.name.replace("models/", "")
                display_name = m.display_name
                input_limit = str(m.input_token_limit)
                
                print(f"{model_id:<25} | {display_name:<30} | {input_limit}")
                found = True

        print("-" * 75)
        
        if found:
            print("\n✅ Tips: USE 'ID MODEL' in file .env GitSage.")
        else:
            print("❌ No model 'generateContent' found.")

    except Exception as e:
        print(f"\n❌ Mistakes found on connection/API: {e}")

if __name__ == "__main__":
    main()