import json
import requests
import os
import time

def load_log(LOG_FILE):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    else:
        return {"tokens_used": 0,"time_taken_last_run": 0.0, "time_taken_total": 0.0, "total_speed_for_response" : 0.0, "runs": 0}

def save_log(LOG_FILE,log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)
        
def server_model_chat(context, prompt, model,temperature, max_tokens, LOG_FILE, seed: int =42, url = 'https://api.llm.ideker.ucsd.edu/api/chat'):
    backoff_time = 10  # Start backoff time at 10 second
    retries = 0
    max_retries = 5
    # set up the log file
    log_data = load_log(LOG_FILE)
    ##load messages 
    messages = [{"role": "system", "content": context},{"role": "user", "content": prompt}]
    # Set up the data for the POST request
    data = {
        "model": model,
        "stream": False,
        "messages":messages,
        "options": {
            "seed": seed,
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }
    while retries < max_retries: ## allow a max of 5 retries if the server is busy or overloaded
        try:
            response = requests.post(url, json = data, timeout= 120)

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
                
                save_log(LOG_FILE,log_data) # save the log
                
                return  analysis, None # second value is error message 
            elif response.status_code in [500, 502, 503, 504]:
                print(f'Encountering server issue {response.status_code}. Retrying in ', backoff_time, ' seconds')
                
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
                
            else:
                error_message = f'The request failed with status code: {response.status_code}'
                print(error_message)
                return None, error_message
        except requests.exceptions.RequestException as e:
            print('The request failed with an exception: ', e, ' Retrying in ', backoff_time, ' seconds')
            time.sleep(backoff_time)
            retries += 1 
            backoff_time *= 2 # Double the backoff time for the next retry
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None, str(e)
    return None, "Error: Max retries exceeded, last response error was: " + str(response.status_code)
