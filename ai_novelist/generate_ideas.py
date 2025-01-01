import json
import os
import os.path as osp
from typing import List, Dict, Union

import backoff
import requests
from ai_novelist.llm import get_response_from_llm, extract_json_between_markers, create_client, AVAILABLE_LLMS

idea_first_prompt = """
# Background
Next year, a spin-off novel based on an original work will be published.
The sales performance of this spin-off novel is crucial as it directly impacts the survival of the company.
Execute the assigned task step by step based on the provided information.

# Task
{task_description}

## Summary of the Original Work:
{summary}

## The Overall Vision of other editors:
I will also share the Overall Vision created by other editors below. 
Please ensure that your proposal takes a completely different direction in every aspect and builds a more compelling Overall Vision.
{prev_idea}

THOUGHT:
<THOUGHT>

NEW OVERALL VISION JSON:
```json
<JSON>
```

In <THOUGHT>, describe your intuition and motivation for creating the Overall Vision.
Afterward, justify why this Overall Vision is compelling and engaging.

In <JSON>, provide a new Overall Vision in JSON format with the following fields:
"Name": "Give a unique name that represents the Overall Vision and does not overlap with others. Use lowercase letters only, and use underscores if necessary. Do not use spaces.",
"theme": "Decide on the overarching theme or message of the story. Examples: love and sacrifice, revenge and forgiveness, self-discovery, the essence of humanity, etc.",
"target_demographics": "Defines the primary audience for the spin-off. Combine age and gender to clearly identify the target group’s characteristics. This helps optimize the story’s tone, theme, and marketing strategy. Example: For teenage females, emphasize youthfulness and romance; for males in their twenties, focus on action and strategic plots.",
"novel_structure_models": "Select a structural model to plan the progression of the story. Examples: Three-Act Structure, Hero's Journey, Kishōtenketsu, etc."
"narrative_perspective": "Determine the perspective from which the story is told. Examples: first-person perspective, third-person perspective (limited or omniscient), second-person perspective, etc."
"core_connection": "Describes how the spin-off ties back to the original work. Leverage popular characters, unresolved storylines, or deeper exploration of the original world to attract fans. Example: Make the rival character the protagonist or create a spin-off that complements the background setting.",
"unique_hook": "Highlights what sets the spin-off apart from both the original and other works. Incorporate novel perspectives or new themes to draw in a broader audience. Example: Depict the story from the antagonist’s point of view or create a comedic spin-off set in everyday life.",
"protagonist_choice": "The selection of the protagonist. Choose a character that easily captures readers’ interest. Candidates include fan-favorite side characters or new ones unexplored in the original. Example: A mysterious character from the original, or an ancestor/descendant from a different era.",
"tone_and_style": "Determines the tone and style of the story, such as serious, comedic, dark, or light. Tailor it to the atmosphere that the audience expects. Example: For dark fantasy, use heavy, detailed descriptions; for romantic comedy, focus on light, playful dialogue.",
"world_expansion": "Explains how the original world will be expanded. Introduce new regions, cultures, or histories to further captivate existing fans. Example: Depict foreign cultures not covered in the original or introduce new technologies or magic.",
"fan_service": "Includes elements that cater to fans of the original work. This could be unresolved plot points, reappearances of beloved characters, or references to specific episodes. Example: Reveal unpublished settings debated among fans, or create new scenes of interaction between popular characters.",

Please ensure that all items except "Name" are described in more detail, with each description being between 100 and 200 characters.

Do not add or remove any of the above items under any circumstances, and ensure to adhere to the format.
"""

idea_reflection_prompt="""Round {current_round}/{num_reflections}.
First, carefully evaluate the Overall Vision you have created based on the following three evaluation criteria and include them as additional fields in the JSON structure.
Also, include other factors that you believe are important for evaluating the idea.
Ensure that the idea is clear and concise, and verify that the JSON is correctly formatted.
Avoid making the content overly complicated.
In the next iteration, aim to refine and improve the idea.
Unless there are significant issues, respect the spirit of the original idea.

# Three Evaluation Criteria:
"Emotion": "The story's ability to captivate the reader's emotions, evoke empathy, and create immersion (rated on a scale of 1 to 10)."
"Market": "How well the idea aligns with the target market and caters to a high-demand theme or setting (rated on a scale of 1 to 10)."
"Novelty": "The originality and creativity of the idea, and how well it differentiates itself from other works (rated on a scale of 1 to 10)."

Respond in the same format as before:
THOUGHT:
<THOUGHT>

NEW IDEA JSON:
```json
<JSON>
```

# Check
Check if the JSON items match the following list and ensure there are no additions or omissions.
"Name","theme","target_demographics","novel_structure_models","narrative_perspective",
"core_connection","unique_hook","protagonist_choice","tone_and_style","world_expansion",
"fan_service","Emotion","Market","Novelty"

If there is nothing to improve, simply repeat the previous JSON EXACTLY after the thought and include "I am done" at the end of the thoughts but before the JSON.
ONLY INCLUDE "I am done" IF YOU ARE MAKING NO MORE CHANGES.
"""

def generate_ideas(
    base_dir: str,
    client,
    model: str,
    skip_generation: bool = False,
    max_num_generations: int = 5,
    num_reflections: int = 5
) -> List[Dict]:
    """
    Generate ideas using a language model based on provided prompts and seed data.

    This function reads prompts and seed ideas from files, generates new ideas iteratively,
    and refines them through multiple reflections. The results are saved as JSON files
    in the specified directory.

    Args:
        base_dir (str): The base directory containing input files and where results will be saved.
        client: The client object for interacting with the language model.
        model (str): The name of the language model to use.
        skip_generation (bool): Whether to skip idea generation and use existing ideas. Default is False.
        max_num_generations (int): Maximum number of ideas to generate. Default is 20.
        num_reflections (int): Number of iterative refinements per idea. Default is 5.

    Returns:
        List[Dict]: A list of generated ideas, each represented as a dictionary.

    Raises:
        FileNotFoundError: If required input files are missing.
        AssertionError: If JSON extraction from LLM output fails.
    """
    if skip_generation:
        try:
            with open(osp.join(base_dir, "ideas.json"), "r") as f:
                ideas = json.load(f)
            print("Loaded existing ideas:")
            for idea in ideas:
                print(idea)
            return ideas
        except FileNotFoundError:
            print("No existing ideas found. Generating new ideas.")
        except json.JSONDecodeError:
            print("Error decoding existing ideas. Generating new ideas.")
            
    idea_str_archive = []
    with open(osp.join(base_dir, "prompt.json"), "r") as f:
        prompt = json.load(f)

    with open(osp.join(base_dir, "original_work_info.json"), "r") as f:
        original_work = json.load(f)
     
    prev_idea = ""   
    seed_path = osp.join(base_dir, "seed_idea.json")
    if osp.exists(seed_path):
        with open(seed_path, "r") as f:
            seed_ideas = json.load(f)
        items = []
        for seed_idea in seed_ideas:
            items.append(json.dumps(seed_idea))
        prev_idea = "\n\n".join(items)

    for i in range(max_num_generations):
        print()
        print(f"Generating idea {i + 1}/{max_num_generations}")
        try:
            msg_history = []
            print(f"Iteration 1/{num_reflections}")
            text, msg_history = get_response_from_llm(
                idea_first_prompt.format(
                    task_description=prompt["task_description"],
                    summary=original_work["summary"],
                    prev_idea=prev_idea,
                    num_reflections=num_reflections,
                ),
                client=client,
                model=model,
                system_message=prompt["system"],
                msg_history=msg_history,
            )
            json_output = extract_json_between_markers(text)
            assert json_output is not None, "Failed to extract JSON from LLM output"
            items = []
            for o in json_output:
                items.append(json.dumps(o))
            prev_idea = "\n\n".join(items)

            if num_reflections > 1:
                for j in range(num_reflections - 1):
                    print(f"Iteration {j + 2}/{num_reflections}")
                    text, msg_history = get_response_from_llm(
                        idea_reflection_prompt.format(
                            current_round=j + 2, num_reflections=num_reflections
                        ),
                        client=client,
                        model=model,
                        system_message= prompt["system"],
                        msg_history=msg_history,
                    )
                    json_output = extract_json_between_markers(text)
                    assert (
                        json_output is not None
                    ), "Failed to extract JSON from LLM output"
                    print(json_output)

                    if "I am done" in text:
                        print(f"Idea generation converged after {j + 2} iterations.")
                        break

            idea_str_archive.append(json.dumps(json_output))
        except Exception as e:
            print(f"Failed to generate idea: {e}")
            continue

    ideas = [json.loads(idea_str) for idea_str in idea_str_archive]

    with open(osp.join(base_dir, "ideas.json"), "w") as f:
        json.dump(ideas, f, indent=4)

    return ideas

if __name__ == "__main__":
    MAX_NUM_GENERATIONS = 10
    NUM_REFLECTIONS = 2

    parser = argparse.ArgumentParser(description="Generate ideas for AI-based scientific experiments.")
    parser.add_argument(
        "--experiment",
        type=str,
        default="fascinating_spin_off",
        help="Experiment to run AI Novelist on."
    )
    parser.add_argument(
        "--model",
        type=str,
        default="deepseek-coder-v2-0724",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Novelist."
    )
    parser.add_argument(
        "--skip-idea-generation",
        action="store_true",
        help="Skip idea generation and use existing ideas."
    )
    args = parser.parse_args()

    client, client_model = create_client(args.model)

    base_dir = osp.join("templates", args.experiment)
    results_dir = osp.join("results", args.experiment)
    ideas = generate_ideas(
        base_dir,
        client=client,
        model=client_model,
        skip_generation=args.skip_idea_generation,
        max_num_generations=MAX_NUM_GENERATIONS,
        num_reflections=NUM_REFLECTIONS,
    )

