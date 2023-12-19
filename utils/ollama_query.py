import json
import requests
import os

def load_log_gort(LOG_FILE):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    else:
        return {"tokens_used": 0,"time_taken_last_run": 0.0, "time_taken_total": 0.0, "total_speed_for_response" : 0.0, "runs": 0}

def save_log_gort(LOG_FILE,log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)
        
def query_gort_model(context, prompt, model,temperature, LOG_FILE, seed: int =42):
    # set up the log file
    log_data = load_log_gort(LOG_FILE)
    ##load messages 
    messages = [{"role": "system", "content": context},{"role": "user", "content": prompt}]
    # Set up the data for the POST request
    data = {
        "model": model,
        "stream": False,
        "messages":messages,
        "options": {
            "seed": seed,
            "temperature": temperature
        }
    }
    url = 'https://ollama-api.ideker.ucsd.edu/api/chat'
    response = requests.post(url, json = data)

    # Check if the request was successful
    if response.status_code == 200:
        # return the response
        # print(response.json())
        output = response.json()
        analysis = output['message']['content'] 
        total_duration = output['total_duration']
        total_tokens = output['prompt_eval_count'] + output['eval_count']
        response_speed = output['eval_count']/output['eval_duration']
        # response_embedding = output.get('context', None)
        # update the log
        log_data["tokens_used"] += total_tokens
        log_data["time_taken_last_run"] = total_duration
        log_data["time_taken_total"] += total_duration
        log_data["total_speed_for_response"] += response_speed
        log_data["runs"] += 1
        
        save_log_gort(LOG_FILE,log_data) # save the log
        
        return  analysis
    else:
        print(f"Error: {response.status_code}")
        return None
