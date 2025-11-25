import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Load env
load_dotenv()


async def test_gemini():
    print("Testing Gemini Integration...")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables.")
        return

    print(f"✅ GOOGLE_API_KEY found: {api_key[:5]}...")

    # Test LLM
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key
        )
        response = llm.invoke("Hello, are you working?")
        print(f"✅ LLM Response: {response.content}")
    except Exception as e:
        print(f"❌ LLM Error: {e}")

    # Test Embeddings
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=api_key
        )
        vector = embeddings.embed_query("Hello world")
        print(f"✅ Embeddings generated. Vector length: {len(vector)}")
    except Exception as e:
        print(f"❌ Embeddings Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_gemini())
