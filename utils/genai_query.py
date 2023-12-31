import os 
import google.generativeai as genai 
import time
import json
import re

def load_log(LOG_FILE):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    else:
        return {"tokens_used": 0 ,"time_taken_last_run": 0.0, "time_taken_total": 0.0, "runs": 0}

def save_log(LOG_FILE,log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)

def query_genai_model(prompt, model, temperature, max_tokens,LOG_FILE):
    '''
    prompt = context + prompt
    model = 'gemini-pro' for now 20231226
    temperature: set the temperature for the model for determining the randomness of the output.
    max_tokens: set the maximum number of tokens to generate for the output.
    LOG_FILE: the log file to save the log data
    '''
    # configuration load key  
    genai.configure(api_key=os.getenv('GOOGLEAI_KEY'))

    #set up model 
    model = genai.GenerativeModel('gemini-pro')
    #define message 
    messages = [
        # {'role':'system',
        #  'parts': "You are an efficient and insightful assistant to a molecular biologist"},
        {'role':'user',
        'parts': prompt}
        ]

    start_time = time.time()
    try:
        response = model.generate_content(
            messages, 
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens, temperature=temperature
            )
        )
    except Exception as e:
        # Handle specific exceptions as needed
        print(f'Encountered an error: {e}')
        return None, str(e)
    
    end_time = time.time()
    input_tokens= model.count_tokens(prompt).total_tokens
   
    total_duration = end_time - start_time
    response_content = response.text
    if response_content:
        output_tokens = model.count_tokens(response_content).total_tokens
        
        total_tokens = input_tokens + output_tokens
        # save the log
        log_data = load_log(LOG_FILE)
        log_data["tokens_used"] += total_tokens
        log_data["time_taken_last_run"] = total_duration
        log_data["time_taken_total"] += total_duration
        log_data["runs"] += 1
        save_log(LOG_FILE,log_data)
        return response_content, None
    else:
        total_tokens = input_tokens
        log_data = load_log(LOG_FILE)
        log_data["tokens_used"] += total_tokens
        log_data["time_taken_last_run"] = total_duration
        log_data["time_taken_total"] += total_duration
        log_data["runs"] += 1
        save_log(LOG_FILE,log_data)
        return None, response._error
    
    
