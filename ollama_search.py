#!/usr/bin/env python3
from serve_hybrid import semantic_search, hybrid_search, print_timing_report
import requests
import json
import sys

def query_ollama(prompt, model="qwen3:4b"):
    """Query Ollama with given prompt"""
    print("Sending request to Ollama...", file=sys.stderr)
    try:
        # Add specific instructions to avoid thinking process
        enhanced_prompt = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 1024,
                "stop": ["<think>", "</think>", "You:", "Human:"]
            }
        }
        
        response = requests.post('http://localhost:11434/api/generate',
                               json=enhanced_prompt,
                               timeout=30)
        
        print("Got response from Ollama", file=sys.stderr)
        if response.status_code != 200:
            print(f"Error: Ollama returned status code {response.status_code}", file=sys.stderr)
            return f"Error: Could not process request. Falling back to direct search.\n\n[SEARCH]{prompt.split('"content": "')[-1].split('"')[0]}[/SEARCH]"
            
        response_text = response.json()['response']
        
        # Additional cleaning of common issues
        response_text = response_text.replace("<think>", "").replace("</think>", "")
        response_text = response_text.replace("Assistant:", "").replace("You:", "")
        response_text = "\n".join(line for line in response_text.split("\n") if not line.strip().startswith("Human:"))
        
        return response_text.strip()
        
    except requests.exceptions.Timeout:
        print("Error: Ollama request timed out", file=sys.stderr)
        return f"Timeout error. Falling back to direct search.\n\n[SEARCH]{prompt.split('"content": "')[-1].split('"')[0]}[/SEARCH]"
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama. Is it running?", file=sys.stderr)
        return "Error: Could not connect to Ollama. Please make sure it's running on localhost:11434"
    except Exception as e:
        print(f"Error querying Ollama: {str(e)}", file=sys.stderr)
        return f"Error: {str(e)}. Falling back to direct search.\n\n[SEARCH]{prompt.split('"content": "')[-1].split('"')[0]}[/SEARCH]"

def create_system_prompt():
    return """You are a technical documentation expert for automotive systems. Your task is to:

1. Search for relevant information using [SEARCH] query [/SEARCH]
2. Analyze search results and explain technical concepts clearly
3. Only reference sections and signals that appear in the results
4. Focus on factual technical details without speculation

Keep responses clear and direct. Avoid unnecessary formatting or markers.
If information is missing from search results, say so explicitly.

Start with a search to gather information."""

def clean_response(response):
    """Clean up the response by removing thinking process and formatting"""
    # Remove everything between <think> tags including the tags
    while "<think>" in response and "</think>" in response:
        start = response.find("<think>")
        end = response.find("</think>") + 8
        response = response[:start] + response[end:]
    
    # Remove any remaining markers
    response = response.replace("<think>", "").replace("</think>", "")
    
    # Remove any lines that are just "A:" or similar
    lines = [line for line in response.split("\n") if not line.strip().lower() in ["a:", "assistant:", "you:"]]
    
    # Clean up markdown separators while preserving technical formatting
    lines = [line for line in lines if not line.strip() == "---"]
    
    # Preserve signal names and technical parameters
    cleaned_lines = []
    for line in lines:
        # Keep lines with technical content
        if any(tech in line for tech in ['`', '[Section', 'Signal:', 'Parameter:', 'Value:']):
            cleaned_lines.append(line)
        # Remove excessive formatting from other lines
        elif line.strip():
            line = line.replace('###', '').replace('**', '')
            cleaned_lines.append(line.strip())
    
    # Join lines with appropriate spacing
    response = "\n".join(cleaned_lines)
    
    # Remove any extra newlines at start/end and collapse multiple newlines
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
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
            
        # Keep conversation history manageable
        if len(conversation) > 6:
            conversation = [
                conversation[0],  # System prompt
                conversation[-2],  # Last user message
                conversation[-1]  # Last assistant message
            ]
        
        # Add user query to conversation
        conversation.append({"role": "user", "content": user_input})
        
        print("\nProcessing your question...", file=sys.stderr)
        
        try:
            # Get Ollama's initial response
            response = query_ollama(json.dumps(conversation))
            if not response or response.isspace():
                # If we get an empty response, fall back to direct search
                print("Got empty response, falling back to direct search", file=sys.stderr)
                results = hybrid_search(user_input)
                print("\nHere are the relevant results:")
                for r in results:
                    print(f"\nSection: {r['section_id']}")
                    print(f"Text: {r['text'][:300]}...")
                    if r['signal_ids']:
                        print(f"Related Signals: {', '.join(r['signal_ids'][:5])}")
                continue
                
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
                    results_text += f"Text: {r['text'][:300]}...\n"
                    results_text += f"Related Signals: {', '.join(r['signal_ids'][:5])}\n"
                
                # Add search results to conversation
                conversation.append({"role": "assistant", "content": response[:start-8]})
                conversation.append({"role": "system", "content": results_text})
                
                # Get next response from Ollama
                print("Getting next response from Ollama...", file=sys.stderr)
                response = query_ollama(json.dumps(conversation))
                if not response or response.isspace():
                    print("Got empty follow-up response", file=sys.stderr)
                    break
                response = clean_response(response)
                response = response[end + 9:].strip()
            
            # Add final response to conversation
            if response and not response.isspace():
                conversation.append({"role": "assistant", "content": response})
                print("\nAssistant:", response)
            
        except Exception as e:
            print(f"\nError during processing: {str(e)}", file=sys.stderr)
            # Fallback to direct search
            results = hybrid_search(user_input)
            print("\nHere are the most relevant results:")
            for r in results:
                print(f"\nSection: {r['section_id']}")
                print(f"Text: {r['text'][:300]}...")
                if r['signal_ids']:
                    print(f"Related Signals: {', '.join(r['signal_ids'][:5])}")
        
        print_timing_report()

if __name__ == "__main__":
    main() 