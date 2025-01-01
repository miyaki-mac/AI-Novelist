import json
import os.path as osp
import shutil
import subprocess
import sys
from subprocess import TimeoutExpired

MAX_ITERS = 3
MAX_RUNS = 3
MAX_STDERR_OUTPUT = 1500

coder_prompt="""
The editor has devised the Overall Vision for the spin-off novel.
For each item listed below, create step-by-step responses and utilize them in the improvement process.
Since these decisions are made by the editor, ensure that all items are fully reflected in the novel.

# Overall vision for a spin-off novel
- narrative_perspective:{narrative_perspective}
- theme:{theme}
- novel_structure_models:{novel_structure_models}
- target_demographics:{target_demographics}
- core_connection:{core_connection}
- unique_hook:{unique_hook}
- protagonist_choice:{protagonist_choice}
- tone_and_style:{tone_and_style}
- world_expansion:{world_expansion}
- fan_service:{fan_service}

Based on the editor's Overall Vision above, appropriately improve the task_prompt_for_writing in experiment.py to ensure the novel fulfills all outlined items, particularly by adhering to the structure defined in novel_structure_models.

Due to the variability in LLM outputs, continue experimenting until all items are satisfied and the novel is deemed engaging. You are allowed a maximum of {max_runs} executions to complete the experiments, but it is not necessary to use all {max_runs}.

After completing each change, execute the command python experiment.py --out_dir=run_i (where i is the run number) and evaluate the results.

Proposed changes must strictly adhere to this command format without including additional command-line arguments.

Afterward, proceed with the next item on your list.
"""

# RUN EXPERIMENT
def run_experiment(folder_name, run_num, timeout=7200):
    # cwd = osp.abspath(folder_name)
    cwd = "./" + folder_name
    # COPY CODE SO WE CAN SEE IT.
    shutil.copy(
        osp.join(folder_name, "experiment.py"),
        osp.join(folder_name, f"run_{run_num}.py"),
    )

    # LAUNCH COMMAND
    command = [
        "python",
        "experiment.py",
        f"--out_dir=run_{run_num}",
    ]
    results = {}
    try:
        result = subprocess.run(
            command, cwd=cwd, stderr=subprocess.PIPE, text=True, timeout=timeout
        )

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"Run {run_num} failed with return code {result.returncode}")
            if osp.exists(osp.join(cwd, f"run_{run_num}")):
                shutil.rmtree(osp.join(cwd, f"run_{run_num}"))
            print(f"Run failed with the following error {result.stderr}")
            stderr_output = result.stderr
            if len(stderr_output) > MAX_STDERR_OUTPUT:
                stderr_output = "..." + stderr_output[-MAX_STDERR_OUTPUT:]
            next_prompt = f"Run failed with the following error {stderr_output}"
        else:
            with open(osp.join(cwd, f"run_{run_num}", "results.json"), "r") as f:
                results = json.load(f)

            next_prompt = f"""Run {run_num} completed. Here are the results:
{results}

Decide if you need to re-plan your experiments given the result (you often will not need to).

Someone else will be using `notes.txt` to perform a writeup on this in the future.
Please include *all* relevant information for the writeup on Run {run_num}, including an experiment description and the run number. Be as verbose as necessary.

Then, implement the next thing on your list.
We will then run the command `python experiment.py --out_dir=run_{run_num + 1}'.
YOUR PROPOSED CHANGE MUST USE THIS COMMAND FORMAT, DO NOT ADD ADDITIONAL COMMAND LINE ARGS.
If you are finished with experiments, respond with 'ALL_COMPLETED'."""
        return result.returncode, next_prompt, results
    except TimeoutExpired:
        print(f"Run {run_num} timed out after {timeout} seconds")
        if osp.exists(osp.join(cwd, f"run_{run_num}")):
            shutil.rmtree(osp.join(cwd, f"run_{run_num}"))
        next_prompt = f"Run timed out after {timeout} seconds"
        return 1, next_prompt, results

# PERFORM EXPERIMENTS
def perform_experiments(idea, folder_name, coder, baseline_results) -> bool:
    ## RUN EXPERIMENT
    current_iter = 0
    run = 1
    next_prompt = coder_prompt.format(
        narrative_perspective=idea["narrative_perspective"],
        theme=idea["theme"],
        novel_structure_models=["novel_structure_models"],
        target_demographics=idea["target_demographics"],
        core_connection=idea["core_connection"],
        unique_hook=idea["unique_hook"],
        protagonist_choice=idea["protagonist_choice"],
        tone_and_style=idea["tone_and_style"],
        world_expansion=idea["world_expansion"],
        fan_service=idea["fan_service"],
        max_runs=MAX_RUNS,
    )
    while run < MAX_RUNS + 1:
        if current_iter >= MAX_ITERS:
            print("Max iterations reached")
            break
        coder_out = coder.run(next_prompt)
        print(coder_out)
        if "ALL_COMPLETED" in coder_out:
            break
        return_code, next_prompt, results = run_experiment(folder_name, run)
        if return_code == 0:
            run += 1
            current_iter = 0
        current_iter += 1
    if current_iter >= MAX_ITERS:
        print("Not all experiments completed.")
        return False, results

    return True, results
