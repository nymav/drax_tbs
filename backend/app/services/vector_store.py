import chromadb
import os
from app.config import VECTOR_DB_DIR
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Any, Optional
import uuid

VECTOR_DIR = Path("data/vector_store")

client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

# Existing PDF functions (keeping your original functionality)
def save_vectors(pdf_id, texts, vectors, metadatas=None):
    collection = client.get_or_create_collection(pdf_id)
    if not metadatas:
        metadatas = [{}] * len(texts)
    for i, (t, v, m) in enumerate(zip(texts, vectors, metadatas)):
        m["page"] = i + 1  # estimate page number
        collection.add(documents=[t], embeddings=[v], metadatas=[m], ids=[f"{pdf_id}_{i}"])

def query_vectors(pdf_id, query_vec, k=10):
    print(f"[VECTOR_STORE] Looking for PDF ID: {pdf_id}")
    print("[VECTOR_STORE] Available store keys:", os.listdir(VECTOR_DIR))

    collection = client.get_or_create_collection(pdf_id)
    return collection.query(
        query_embeddings=[query_vec],
        n_results=k,
        include=["documents", "metadatas"]
    )

# NEW: Conversation Memory Functions
def save_conversation(session_id: str, user_input: str, assistant_response: str, 
                     user_embedding: List[float], response_embedding: List[float],
                     model_used: str = "", tags: List[str] = None):
    """Save a conversation to the vector store for future retrieval"""
    
    # Use a dedicated collection for conversations
    collection_name = f"conversations_{session_id}"
    collection = client.get_or_create_collection(collection_name)
    
    conversation_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Store both user input and assistant response as separate vectors
    # This allows searching by either user questions or assistant answers
    
    # Store user input
    user_metadata = {
        "type": "user_input",
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "model_used": model_used,
        "tags": json.dumps(tags) if tags else "[]",
        "paired_response": assistant_response[:200] + "..." if len(assistant_response) > 200 else assistant_response
    }
    
    collection.add(
        documents=[user_input],
        embeddings=[user_embedding],
        metadatas=[user_metadata],
        ids=[f"{conversation_id}_user"]
    )
    
    # Store assistant response
    response_metadata = {
        "type": "assistant_response", 
        "conversation_id": conversation_id,
        "timestamp": timestamp,
        "model_used": model_used,
        "tags": json.dumps(tags) if tags else "[]",
        "paired_input": user_input[:200] + "..." if len(user_input) > 200 else user_input
    }
    
    collection.add(
        documents=[assistant_response],
        embeddings=[response_embedding], 
        metadatas=[response_metadata],
        ids=[f"{conversation_id}_response"]
    )
    
    print(f"💾 Saved conversation to session: {session_id}")
    return conversation_id

def find_similar_conversations(session_id: str, query_embedding: List[float], 
                             k: int = 5, search_type: str = "both") -> List[Dict]:
    """Find similar past conversations using vector similarity"""
    
    collection_name = f"conversations_{session_id}"
    try:
        collection = client.get_collection(collection_name)
    except:
        print(f"No conversation history found for session: {session_id}")
        return []
    
    # Query the collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k * 2,  # Get more results to filter by type
        include=["documents", "metadatas", "distances"]
    )
    
    if not results['documents'] or not results['documents'][0]:
        return []
    
    # Process results
    similar_conversations = []
    seen_conversation_ids = set()
    
    for doc, metadata, distance in zip(results['documents'][0], 
                                     results['metadatas'][0], 
                                     results['distances'][0]):
        
        # Filter by search type
        if search_type == "user_only" and metadata["type"] != "user_input":
            continue
        elif search_type == "response_only" and metadata["type"] != "assistant_response":
            continue
        
        conv_id = metadata["conversation_id"]
        
        # Avoid duplicate conversations (since we store both user and assistant parts)
        if conv_id in seen_conversation_ids:
            continue
        seen_conversation_ids.add(conv_id)
        
        similar_conversations.append({
            "conversation_id": conv_id,
            "document": doc,
            "metadata": metadata,
            "similarity_score": 1 - distance,  # Convert distance to similarity
            "timestamp": metadata["timestamp"],
            "model_used": metadata["model_used"],
            "type": metadata["type"]
        })
        
        if len(similar_conversations) >= k:
            break
    
    return similar_conversations

def get_conversation_context(session_id: str, query_embedding: List[float], 
                           max_context_length: int = 1500) -> str:
    """Get relevant context from past conversations for the current query"""
    
    similar_convs = find_similar_conversations(session_id, query_embedding, k=3)
    
    if not similar_convs:
        return ""
    
    context_parts = []
    current_length = 0
    
    for conv in similar_convs:
        # Build context from similar conversations
        if conv["type"] == "user_input":
            context_text = f"Past Question: {conv['document']}\nPast Answer: {conv['metadata']['paired_response']}\n---\n"
        else:  # assistant_response
            context_text = f"Past Question: {conv['metadata']['paired_input']}\nPast Answer: {conv['document']}\n---\n"
        
        if current_length + len(context_text) > max_context_length:
            break
            
        context_parts.append(context_text)
        current_length += len(context_text)
    
    if context_parts:
        return "Relevant conversation history:\n" + "".join(context_parts) + "\nCurrent question:\n"
    
    return ""

def search_conversations_by_text(session_id: str, search_text: str, k: int = 10) -> List[Dict]:
    """Search conversations by text content (without embeddings)"""
    
    collection_name = f"conversations_{session_id}"
    try:
        collection = client.get_collection(collection_name)
    except:
        return []
    
    # Get all documents and filter by text content
    all_results = collection.get(include=["documents", "metadatas"])
    
    matching_conversations = []
    search_lower = search_text.lower()
    
    for doc, metadata in zip(all_results['documents'], all_results['metadatas']):
        if search_lower in doc.lower():
            matching_conversations.append({
                "document": doc,
                "metadata": metadata,
                "conversation_id": metadata["conversation_id"],
                "timestamp": metadata["timestamp"],
                "type": metadata["type"]
            })
    
    # Sort by timestamp (most recent first)
    matching_conversations.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return matching_conversations[:k]

def get_conversation_stats(session_id: str) -> Dict:
    """Get statistics about stored conversations"""
    
    collection_name = f"conversations_{session_id}"
    try:
        collection = client.get_collection(collection_name)
        all_results = collection.get(include=["metadatas"])
        
        if not all_results['metadatas']:
            return {"total_conversations": 0, "total_entries": 0}
        
        # Count unique conversations
        conversation_ids = set()
        model_usage = {}
        
        for metadata in all_results['metadatas']:
            conversation_ids.add(metadata["conversation_id"])
            model = metadata.get("model_used", "unknown")
            model_usage[model] = model_usage.get(model, 0) + 1
        
        return {
            "total_conversations": len(conversation_ids),
            "total_entries": len(all_results['metadatas']),
            "model_usage": model_usage,
            "session_id": session_id
        }
    
    except:
        return {"total_conversations": 0, "total_entries": 0, "session_id": session_id}

def clear_conversation_history(session_id: str) -> bool:
    """Clear all conversation history for a session"""
    
    collection_name = f"conversations_{session_id}"
    try:
        client.delete_collection(collection_name)
        print(f"🗑️ Cleared conversation history for session: {session_id}")
        return True
    except Exception as e:
        print(f"❌ Error clearing history: {e}")
        return False

def list_all_sessions() -> List[str]:
    """List all conversation sessions"""
    collections = client.list_collections()
    sessions = []
    
    for collection in collections:
        if collection.name.startswith("conversations_"):
            session_id = collection.name.replace("conversations_", "")
            sessions.append(session_id)
    
    return sessions

# Utility function to integrate with your existing LLM code
def get_memory_enhanced_prompt(session_id: str, user_input: str, 
                              query_embedding: List[float], 
                              use_memory: bool = True) -> str:
    """
    Enhance a user prompt with relevant conversation context
    This function can be called before sending to ask_local_llm()
    """
    
    if not use_memory:
        return user_input
    
    # Get relevant context from past conversations
    context = get_conversation_context(session_id, query_embedding)
    
    if context:
        return f"{context}{user_input}"
    else:
        return user_input