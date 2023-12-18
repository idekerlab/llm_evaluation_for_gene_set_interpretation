import json
import openai
import os
import time 
import argparse
import requests


def load_log(LOG_FILE):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    else:
        return {"tokens_used": 0, "dollars_spent": 0.0, "time_taken_last_run": 0.0, "time_taken_total": 0.0, "runs": 0}

def save_log(LOG_FILE,log_data):
    with open(LOG_FILE, "w") as f:
        json.dump(log_data, f, indent=4)

def estimate_cost(tokens, rate_per_token):
    return tokens * rate_per_token

def openai_chat(context, prompt, model,temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT, seed: int = None):
    backoff_time = 10  # Start backoff time at 10 second
    retries = 0

    
    log_data = load_log(LOG_FILE)
    tokens_estimate = len(prompt) + max_tokens

    if estimate_cost(log_data["tokens_used"] + tokens_estimate, rate_per_token) > DOLLAR_LIMIT:
        print("The API call is estimated to exceed the dollar limit. Aborting.")
        return
    while retries <= 5: ## allow a max of 5 retries if the server is busy or overloaded
        try:
            start_time = time.time()
            response = openai.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": context},{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                n=1,
                stop=None,
                seed=seed,
                temperature=temperature,
            )
            end_time = time.time() 
            
            # print(response)
            # tokens_used = response["usage"]["total_tokens"]
            tokens_used = response.usage.total_tokens
            response_content = response.choices[0].message.content
            system_fingerprint = response.system_fingerprint
            # Update and save the log
            log_data["tokens_used"] += tokens_used
            log_data["dollars_spent"] = estimate_cost(log_data["tokens_used"], rate_per_token)
            time_usage = end_time - start_time
            log_data["time_taken_last_run"] = time_usage
            log_data["time_taken_total"] += time_usage
            log_data["runs"] += 1 # Increment the number of runs, used for estimating the average time taken per run
            print(tokens_used)
            save_log(LOG_FILE,log_data)

            return response_content, system_fingerprint
        except requests.exceptions.RequestException as err:
            if err.response.status_code == 429:  # HTTP status 429: Too Many Requests
                error_body = err.response.json()  # Retrieve error body
                error_message = error_body.get('message', '')  # Extract error message
                
                if 'You exceeded your current quota' in error_message: # If the error message indicates that the quota has been exceeded, abort
                    print("You exceeded your current quota, exiting...")
                    return None
                elif 'That model is currently overloaded with other requests.' in error_message:
                    print(f"Server is overloaded, retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    retries += 1
                    backoff_time *= 2 # Double the backoff time for the next retry
            elif err.response.status_code == 500:
                print(f"Server error occurred, retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
            elif err.response.status_code == 502:  # HTTP status 502: Bad Gateway
                print(f"Bad Gateway error occurred, retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
            else:
                print(f"An error occurred: {err}")
                return None, None

        except Exception as e:
            error_message = str(e)
            if 'That model is currently overloaded with other requests.' in error_message or 'The server had an error while processing your request.' in error_message:
                print(f"Server issue occurred, retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
            else:
                print(f"An unknown error occurred: {e}")
                print(f"Retrying in {backoff_time} seconds...")
                time.sleep(backoff_time) # Sleep for the backoff time for error that not seen before and retry until max retries
                retries += 1
                backoff_time *= 2

    print(f"Max retries exceeded. Please try again later.")
    return None, None
    

# excute the script
if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--openai_api_key", type=str, required=True)
    argparser.add_argument("--context", type=str, default=" You are an efficient and insightful assistant to a molecular biologist. You should give the true answer that are supported by the references. If you do not have a clear answer, you will respond with \"Unknown\".")
    argparser.add_argument("--prompt",required=True, type=str, help="input prompt to chatgpt")
    argparser.add_argument("--model", type=str, default="gpt-3.5-turbo")
    argparser.add_argument("--temperature", type=float, default=0, help="temperature for chatgpt to control randomness, 0 means deterministic, 1 means random")
    argparser.add_argument("--max_tokens", type=int, default=500, help="max tokens for chatgpt response")
    argparser.add_argument("--rate_per_token", type=float, default=0.0005, help="rate per token to estimate cost")
    argparser.add_argument("--log_file", type=str, default="./log.json", help="PATH to the log file to save tokens used and dollars spent")
    argparser.add_argument("--dollor_limit", type=float, default=5.0, help="dollor limit to abort the chatgpt query")
    argparser.add_argument("--file_path", type=str, default="./response.txt", help="PATH to the file to save the response")
    
    args = argparser.parse_args()

    openai.api_key = args.openai_api_key

    context = args.context
    prompt = args.prompt
    model = args.model
    temperature = args.temperature
    max_tokens = args.max_tokens
    rate_per_token = args.rate_per_token
    file_path = args.file_path

    LOG_FILE = args.log_file
    DOLLAR_LIMIT = args.dollor_limit
    response_text = openai_chat(context, prompt, model,temperature, max_tokens, rate_per_token, LOG_FILE, DOLLAR_LIMIT)
    if response_text:
        with open(file_path, "w") as f:
            f.write(response_text)
        # print(response_text)
