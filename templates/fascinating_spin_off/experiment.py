import os
import llm
import json
import argparse

system_prompt_for_summary = """
You are an exceptionally talented novel editor responsible for numerous bestselling novels.
"""

task_prompt_for_summary = """
Read the following original work carefully, grasp the characters and the world-building accurately, and summarize it in approximately 300 words.
{text}
"""

system_prompt_for_writing = """
You are a highly popular novelist, and this time, 
you have decided to write a spin-off work based on one of your popular creations.
"""

task_prompt_for_writing = """
Please create a spin-off work based on the original story.
<Summary of the original work>
{text}
</Summary of the original work>
"""

def read_file():
    """
    Reads a novel file from a predefined file path.

    This function attempts to locate and read a novel file. If the file does not
    exist, it raises an error and returns None.

    Returns:
        str: Content of the novel file as a string, or None if the file is not found.

    Raises:
        FileNotFoundError: If the novel file does not exist at the specified path.
    """
    target_path = "/workspace/data/novel/novel.txt"
    file_path = os.path.relpath(target_path, os.getcwd())
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Error: File not found at {file_path}.")

        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError as e:
        print(e)
        return None

def llm_generate(system_prompt, task_prompt, model):
    """
    Sends prompts to the language model and retrieves the generated response.

    Args:
        system_prompt (str): The system prompt to guide the model's behavior.
        task_prompt (str): The task-specific prompt describing the requirements.
        model (str): Name of the model to be used.

    Returns:
        str: The generated response from the language model.
    """
    # Create the LLM client with the specified model
    client, model_name = llm.create_client(model)

    # Generate a response from the language model
    response, _ = llm.get_response_from_llm(
        msg=task_prompt,
        client=client,
        model=model_name,
        system_message=system_prompt,
        temperature=0.2
    )
    return response

def save_file(output_dir, filename, data):
    """
    Saves data to a JSON file.

    Args:
        output_dir (str): Directory where the file will be saved.
        filename (str): Name of the output file.
        data (dict): Data to save.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)

    # Save the data as a JSON file
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def main():
    """
    Main function to orchestrate reading, generating, and saving data.

    This script reads a novel scene, generates prompts for a spin-off story,
    sends them to a language model, and saves the results to a specified directory.

    Command-line Arguments:
        --out_dir (str): Directory where output files will be saved. Default is "run_0".
        --model (str): Name of the model to use. Default is "deepseek-coder-v2-0724".
    """
    parser = argparse.ArgumentParser(
        description="Reads a novel file, generates spin-off prompts based on its content, and uses a language model to create and save a response."
    )
    parser.add_argument("--out_dir", type=str, default="run_0", help="Output directory (default: run_0)")
    parser.add_argument("--model", type=str, default="deepseek-coder-v2-0724", help="Name of the model to use (default: deepseek-coder-v2-0724)")
    args = parser.parse_args()

    print(f"Output directory: {args.out_dir}")
    print(f"Using model: {args.model}")

    # Read the novel text from the file
    novel_text = read_file()
    if not novel_text:
        print("No novel text found. Exiting.")
        return

    # Generate a summary of the novel
    summary = llm_generate(
        system_prompt_for_summary,
        task_prompt_for_summary.format(text=novel_text),
        model=args.model
    )

    # Save the summary to a file
    save_file(os.getcwd(), "original_work_info.json", {"summary": summary})

    # Generate a spin-off based on the summary
    result = llm_generate(
        system_prompt_for_writing,
        task_prompt_for_writing.format(text=summary),
        model=args.model
    )

    # Save the spin-off results to a file
    save_file(args.out_dir, "results.json", {
        "task_prompt": task_prompt_for_writing,
        "model_response": result
    })

if __name__ == "__main__":
    main()