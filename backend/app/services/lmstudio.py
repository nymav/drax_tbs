import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import LMSTUDIO_API

class ModelManager:
    def __init__(self):
        self.current_model = "mistral-7b-instruct"
        self.available_models = []
        self.model_stats = {}
        self.request_history = []
        
    def get_available_models(self) -> List[str]:
        """Fetch available models from LM Studio"""
        try:
            response = requests.get(f"{LMSTUDIO_API.replace('/chat/completions', '')}/models")
            if response.status_code == 200:
                models_data = response.json()
                self.available_models = [model["id"] for model in models_data.get("data", [])]
                print(f"📋 Available models: {self.available_models}")
                return self.available_models
            else:
                print(f"❌ Failed to fetch models: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error fetching models: {e}")
            return []
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        if not self.available_models:
            self.get_available_models()
        
        if model_name in self.available_models or model_name:  # Allow any model name
            self.current_model = model_name
            print(f"🔄 Switched to model: {model_name}")
            return True
        else:
            print(f"❌ Model '{model_name}' not available")
            print(f"Available models: {self.available_models}")
            return False

# Global model manager
model_manager = ModelManager()

def ask_local_llm(prompt: str, **kwargs) -> str:
    """Enhanced LLM interaction with better error handling and features"""
    
    # Extract parameters
    temperature = kwargs.get('temperature', 0.7)
    max_tokens = kwargs.get('max_tokens', 2048)
    model = kwargs.get('model', model_manager.current_model)
    system_message = kwargs.get('system_message', "You are a helpful assistant.")
    timeout = kwargs.get('timeout', 60)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    
    # Add optional parameters if provided
    if 'top_p' in kwargs:
        payload['top_p'] = kwargs['top_p']
    if 'frequency_penalty' in kwargs:
        payload['frequency_penalty'] = kwargs['frequency_penalty']
    if 'presence_penalty' in kwargs:
        payload['presence_penalty'] = kwargs['presence_penalty']
    
    start_time = time.time()
    
    try:
        print(f"🚀 Sending request to: {LMSTUDIO_API}")
        print(f"🤖 Model: {model} | Temp: {temperature} | Max tokens: {max_tokens}")
        
        r = requests.post(LMSTUDIO_API, json=payload, timeout=timeout)
        
        response_time = time.time() - start_time
        
        # Log request for analytics
        model_manager.request_history.append({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_length": len(prompt),
            "response_time": response_time,
            "status_code": r.status_code
        })
        
        # Check if request was successful
        if r.status_code != 200:
            print(f"❌ API Error - Status: {r.status_code}")
            print(f"❌ Response: {r.text}")
            return f"Error: API returned status {r.status_code}"
        
        # Parse JSON response
        try:
            response_json = r.json()
            print(f"✅ Response received in {response_time:.2f}s")
        except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error: {e}")
            print(f"❌ Raw response text: {r.text}")
            return "Error: Invalid JSON response from API"
        
        # Extract response content
        response_content = extract_response_content(response_json)
        
        # Update model stats
        update_model_stats(model, response_time, len(prompt), len(response_content))
        
        return response_content
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Cannot connect to LM Studio API")
        print(f"❌ Check if LM Studio is running on {LMSTUDIO_API}")
        return "Error: Cannot connect to LM Studio. Is it running?"
    except requests.exceptions.Timeout:
        print(f"❌ Timeout Error: LM Studio took longer than {timeout}s to respond")
        return "Error: Request timed out"
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return f"Error: {str(e)}"

def extract_response_content(response_json: Dict) -> str:
    """Extract content from various response formats"""
    # Try different response formats
    if "choices" in response_json:
        # OpenAI format: choices[0].message.content
        return response_json["choices"][0]["message"]["content"]
    elif "response" in response_json:
        # Ollama format: response
        return response_json["response"]
    elif "content" in response_json:
        # Direct content format
        return response_json["content"]
    elif "text" in response_json:
        # Text format
        return response_json["text"]
    elif "answer" in response_json:
        # Answer format
        return response_json["answer"]
    else:
        # Unknown format - print structure for debugging
        print(f"❌ Unknown response format. Keys: {list(response_json.keys())}")
        print(f"❌ Full response: {response_json}")
        return f"Error: Unknown response format. Available keys: {list(response_json.keys())}"

def update_model_stats(model: str, response_time: float, prompt_len: int, response_len: int):
    """Update model performance statistics"""
    if model not in model_manager.model_stats:
        model_manager.model_stats[model] = {
            "total_requests": 0,
            "total_response_time": 0,
            "avg_response_time": 0,
            "total_tokens_processed": 0,
            "avg_tokens_per_second": 0
        }
    
    stats = model_manager.model_stats[model]
    stats["total_requests"] += 1
    stats["total_response_time"] += response_time
    stats["avg_response_time"] = stats["total_response_time"] / stats["total_requests"]
    stats["total_tokens_processed"] += prompt_len + response_len
    
    if response_time > 0:
        stats["avg_tokens_per_second"] = (prompt_len + response_len) / response_time

def get_model_stats(model: str = None) -> Dict:
    """Get performance statistics for a model"""
    if model:
        return model_manager.model_stats.get(model, {})
    return model_manager.model_stats

def ask_streaming_llm(prompt: str, **kwargs):
    """Stream response from LLM (generator function)"""
    payload = {
        "model": kwargs.get('model', model_manager.current_model),
        "messages": [
            {"role": "system", "content": kwargs.get('system_message', "You are a helpful assistant.")},
            {"role": "user", "content": prompt},
        ],
        "temperature": kwargs.get('temperature', 0.7),
        "max_tokens": kwargs.get('max_tokens', 2048),
        "stream": True,
    }
    
    try:
        response = requests.post(LMSTUDIO_API, json=payload, stream=True, timeout=60)
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'choices' in data and data['choices']:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        yield f"Error: {str(e)}"

def batch_process_prompts(prompts: List[str], **kwargs) -> List[str]:
    """Process multiple prompts efficiently"""
    results = []
    total = len(prompts)
    
    print(f"🔄 Processing {total} prompts...")
    
    for i, prompt in enumerate(prompts, 1):
        print(f"📝 Processing {i}/{total}")
        result = ask_local_llm(prompt, **kwargs)
        results.append(result)
        
        # Optional delay between requests
        if kwargs.get('delay', 0) > 0:
            time.sleep(kwargs['delay'])
    
    print(f"✅ Completed processing {total} prompts")
    return results

def prepare_fine_tuning_data(conversations: List[Dict], output_path: str = "training_data.jsonl"):
    """Prepare data for fine-tuning in JSONL format"""
    training_examples = []
    
    for conv in conversations:
        # Convert to chat format
        example = {
            "messages": [
                {"role": "system", "content": conv.get("system", "You are a helpful assistant.")},
                {"role": "user", "content": conv["input"]},
                {"role": "assistant", "content": conv["output"]}
            ]
        }
        training_examples.append(example)
    
    # Save as JSONL
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in training_examples:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"✅ Training data saved: {output_path}")
    print(f"📊 Total examples: {len(training_examples)}")
    
    return output_path

def validate_training_data(file_path: str) -> Dict[str, Any]:
    """Validate training data format and quality"""
    with open(file_path, 'r', encoding='utf-8') as f:
        examples = [json.loads(line) for line in f]
    
    stats = {
        "total_examples": len(examples),
        "avg_input_length": 0,
        "avg_output_length": 0,
        "format_errors": [],
        "quality_issues": []
    }
    
    input_lengths = []
    output_lengths = []
    
    for i, example in enumerate(examples):
        try:
            messages = example["messages"]
            user_msg = next(msg for msg in messages if msg["role"] == "user")
            assistant_msg = next(msg for msg in messages if msg["role"] == "assistant")
            
            input_len = len(user_msg["content"])
            output_len = len(assistant_msg["content"])
            
            input_lengths.append(input_len)
            output_lengths.append(output_len)
            
            # Check for quality issues
            if output_len < 10:
                stats["quality_issues"].append(f"Example {i}: Very short response")
            if input_len > 4000:
                stats["quality_issues"].append(f"Example {i}: Very long input")
                
        except Exception as e:
            stats["format_errors"].append(f"Example {i}: {str(e)}")
    
    if input_lengths:
        stats["avg_input_length"] = sum(input_lengths) / len(input_lengths)
        stats["avg_output_length"] = sum(output_lengths) / len(output_lengths)
    
    print(f"📊 Validation Results:")
    print(f"   Total examples: {stats['total_examples']}")
    print(f"   Avg input length: {stats['avg_input_length']:.1f}")
    print(f"   Avg output length: {stats['avg_output_length']:.1f}")
    print(f"   Format errors: {len(stats['format_errors'])}")
    print(f"   Quality issues: {len(stats['quality_issues'])}")
    
    return stats

def test_model_performance(test_cases: List[Dict], model: str = None) -> Dict:
    """Test model performance on specific cases"""
    if model:
        original_model = model_manager.current_model
        model_manager.switch_model(model)
    
    results = {
        "total_tests": len(test_cases),
        "passed": 0,
        "failed": 0,
        "avg_response_time": 0,
        "details": []
    }
    
    total_time = 0
    
    for i, test_case in enumerate(test_cases):
        start_time = time.time()
        response = ask_local_llm(test_case["input"])
        response_time = time.time() - start_time
        total_time += response_time
        
        # Simple evaluation - you can make this more sophisticated
        expected = test_case.get("expected", "").lower()
        passed = expected in response.lower() if expected else True
        
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append({
            "test_id": i,
            "input": test_case["input"],
            "response": response,
            "expected": test_case.get("expected", ""),
            "passed": passed,
            "response_time": response_time
        })
    
    results["avg_response_time"] = total_time / len(test_cases)
    
    # Restore original model if changed
    if model:
        model_manager.switch_model(original_model)
    
    print(f"🧪 Test Results: {results['passed']}/{results['total_tests']} passed")
    print(f"⏱️ Average response time: {results['avg_response_time']:.2f}s")
    
    return results

def export_conversation_logs(output_path: str = "conversation_logs.json"):
    """Export request history for analysis"""
    with open(output_path, 'w') as f:
        json.dump({
            "request_history": model_manager.request_history,
            "model_stats": model_manager.model_stats,
            "export_time": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"📁 Logs exported to: {output_path}")

# Convenience functions for common use cases
def ask_with_context(question: str, context: str, **kwargs) -> str:
    """Ask a question with specific context"""
    prompt = f"Context: {context}\n\nQuestion: {question}\n\nAnswer:"
    return ask_local_llm(prompt, **kwargs)

def ask_for_summary(text: str, max_length: int = 200, **kwargs) -> str:
    """Generate a summary of given text"""
    prompt = f"Summarize the following text in no more than {max_length} words:\n\n{text}"
    return ask_local_llm(prompt, **kwargs)

def ask_multiple_choice(question: str, options: List[str], **kwargs) -> str:
    """Ask a multiple choice question"""
    options_text = "\n".join([f"{chr(65+i)}. {option}" for i, option in enumerate(options)])
    prompt = f"{question}\n\n{options_text}\n\nAnswer:"
    return ask_local_llm(prompt, **kwargs)