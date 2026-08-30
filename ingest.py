import chromadb
import ollama
import os

# Инициализируем базу данных (хранится в папке chroma_db)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="my_knowledge")

def add_to_db(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                text = f.read()
                # Генерируем вектор (embedding) через Ollama
                response = ollama.embeddings(model="nomic-embed-text", prompt=text)
                embedding = response["embedding"]
                
                # Сохраняем в базу
                collection.add(
                    ids=[filename],
                    embeddings=[embedding],
                    documents=[text]
                )
    print("База знаний обновлена!")

if __name__ == "__main__":
    add_to_db("./knowledge")