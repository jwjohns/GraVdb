#!/usr/bin/env python3
from serve_hybrid import semantic_search, hybrid_search, print_timing_report
import requests
import json
import sys

def query_ollama(prompt, model="qwen3:30b"):
    """Query Ollama with given prompt"""
    print("Sending request to Ollama...", file=sys.stderr)
    try:
        response = requests.post('http://localhost:11434/api/generate',
                               json={
                                   "model": model,
                                   "prompt": prompt,
                                   "stream": False
                               },
                               timeout=30)  # Add timeout
        print("Got response from Ollama", file=sys.stderr)
        return response.json()['response']
    except requests.exceptions.Timeout:
        print("Error: Ollama request timed out after 30 seconds", file=sys.stderr)
        return "I apologize, but I'm having trouble processing your request. Let me try a simpler search. [SEARCH]coolant temperature monitoring basic[/SEARCH]"
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama. Is it running?", file=sys.stderr)
        return "Error: Could not connect to Ollama. Please make sure it's running on localhost:11434"
    except Exception as e:
        print(f"Error querying Ollama: {str(e)}", file=sys.stderr)
        return f"Error: {str(e)}"

def create_system_prompt():
    return """You are an expert automotive systems analyst with deep knowledge of engine control systems.
You have access to a technical documentation search system. When answering questions:
1. You can search the documentation multiple times to gather information
2. You can follow relationships between signals, sections, and components
3. You should cite specific sections and signals you find
4. Explain technical concepts clearly but accurately

To search, use the format: [SEARCH] your search query [/SEARCH]
I will return the results, which you can use to formulate your response or perform additional searches.

Start your response with a search to gather relevant information.
"""

def clean_response(response):
    """Clean up the response by removing thinking process and formatting"""
    # Remove thinking process if present
    if "<think>" in response and "</think>" in response:
        start = response.find("<think>")
        end = response.find("</think>") + 8
        response = response[:start] + response[end:]
    
    # Clean up any remaining markers
    response = response.replace("<think>", "").replace("</think>", "")
    
    # Remove extra newlines and clean up formatting
    response = "\n".join(line for line in response.split("\n") if line.strip())
    
    return response.strip()

def main():
    print("\nAutomotive Technical Documentation Assistant")
    print("-------------------------------------------")
    print("Type your question (or 'quit' to exit)")
    
    # Initialize conversation with system prompt
    conversation = [{"role": "system", "content": create_system_prompt()}]
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
            
        # Add user query to conversation
        conversation.append({"role": "user", "content": user_input})
        
        print("\nProcessing your question...", file=sys.stderr)
        
        # Get Ollama's initial response
        response = query_ollama(json.dumps(conversation))
        response = clean_response(response)
        print("Initial response received", file=sys.stderr)
        
        # Process any search requests
        while "[SEARCH]" in response:
            start = response.find("[SEARCH]") + 8
            end = response.find("[/SEARCH]")
            if end == -1:
                break
                
            search_query = response[start:end].strip()
            print(f"\nSearching for: {search_query}")
            
            # Perform search and get results
            results = hybrid_search(search_query)
            
            # Format results for Ollama
            results_text = "\nSearch Results:\n"
            for r in results:
                results_text += f"\nDocument {r['chunk_id']} (Score: {r['score']:.3f}):\n"
                results_text += f"Section: {r['section_id']}\n"
                results_text += f"Text: {r['text'][:500]}...\n"
                results_text += f"Related Signals: {', '.join(r['signal_ids'][:10])}\n"
            
            # Add search results to conversation
            conversation.append({"role": "assistant", "content": response[:start-8]})
            conversation.append({"role": "system", "content": results_text})
            
            # Get next response from Ollama
            print("Getting next response from Ollama...", file=sys.stderr)
            response = query_ollama(json.dumps(conversation))
            response = clean_response(response)
            response = response[end + 9:].strip()
        
        # Add final response to conversation
        conversation.append({"role": "assistant", "content": response})
        print("\nAssistant:", response)
        print_timing_report()

if __name__ == "__main__":
    main() 