import argparse
import json
import os
import os.path as osp
import re
import shutil
import subprocess
from typing import Optional, Tuple

from ai_novelist.llm import get_response_from_llm, extract_json_between_markers, create_client, AVAILABLE_LLMS


# GENERATE LATEX
def generate_latex(coder, folder_name, pdf_file, timeout=30, num_error_corrections=5):
    folder = osp.abspath(folder_name)
    cwd = osp.join(folder, "latex")  # Fixed potential issue with path
    writeup_file = osp.join(cwd, "template.tex")

    # Remove duplicate figures.
    with open(writeup_file, "r") as f:
        tex_text = f.read()
    referenced_figs = re.findall(r"\\includegraphics.*?{(.*?)}", tex_text)
    duplicates = {x for x in referenced_figs if referenced_figs.count(x) > 1}
    if duplicates:
        for dup in duplicates:
            print(f"Duplicate figure found: {dup}.")
            prompt = f"""Duplicate figures found: {dup}. Ensure any figure is only included once.
If duplicated, identify the best location for the figure and remove any other."""
            coder.run(prompt)

    # Remove duplicate section headers.
    with open(writeup_file, "r") as f:
        tex_text = f.read()
    sections = re.findall(r"\\section{([^}]*)}", tex_text)
    duplicates = {x for x in sections if sections.count(x) > 1}
    if duplicates:
        for dup in duplicates:
            print(f"Duplicate section header found: {dup}")
            prompt = f"""Duplicate section header found: {dup}. Ensure any section header is declared once.
If duplicated, identify the best location for the section header and remove any other."""
            coder.run(prompt)

    # Iteratively fix any LaTeX bugs
    for i in range(num_error_corrections):
        # Filter trivial bugs in chktex
        check_output = os.popen(f"chktex {writeup_file} -q -n2 -n24 -n13 -n1").read()
        if check_output:
            prompt = f"""Please fix the following LaTeX errors in `template.tex` guided by the output of `chktek`:
{check_output}.

Make the minimal fix required and do not remove or change any packages.
Pay attention to any accidental uses of HTML syntax, e.g. </end instead of \\end.
"""
            coder.run(prompt)
        else:
            break
    compile_latex(cwd, pdf_file, timeout=timeout)


def compile_latex(cwd, pdf_file, timeout=30):
    print("GENERATING LATEX")

    commands = [
        ["pdflatex", "-interaction=nonstopmode", "template.tex"],
        ["pdflatex", "-interaction=nonstopmode", "template.tex"],
        ["pdflatex", "-interaction=nonstopmode", "template.tex"],
    ]

    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            print("Standard Output:\n", result.stdout)
            print("Standard Error:\n", result.stderr)
        except subprocess.TimeoutExpired:
            print(f"Latex timed out after {timeout} seconds")
        except subprocess.CalledProcessError as e:
            print(f"Error running command {' '.join(command)}: {e}")

    print("FINISHED GENERATING LATEX")

    # Attempt to move the PDF to the desired location
    try:
        shutil.move(osp.join(cwd, "template.pdf"), pdf_file)
    except FileNotFoundError:
        print("Failed to rename PDF.")

# PERFORM WRITEUP
def perform_writeup(idea, folder_name, coder, results, num_cite_rounds=20):
    
    idea_text = "\n".join([f"{key}: {value}" for key, value in idea.items() if isinstance(value, str)])
    
    # error_list_for_tex = """
    # - LaTeX syntax errors
    # - Unnecessary verbosity or repetition, unclear text
    # - Duplicate headers, e.g. duplicated \\section{{Introduction}} or \\end{{document}}
    # - Unescaped symbols, e.g. shakespeare_char should be shakespeare\\_char in text
    # - Incorrect closing of environments, e.g. </end{{figure}}> instead of \\end{{figure}}
    # """

    # error_list_for_novel = """
    # - The Overall Vision created by the editor is not fully or partially reflected.
    #   Overall Vision:{idea_text}
    # - The connections between chapters are inconsistent or disjointed.
    # - The word count of each chapter falls below 300 characters.
    # - The title does not accurately reflect the overall content of the novel.
    # """
    
    error_list = """
    To prepare the novel for publication, it is necessary to improve its quality. 
    Please carefully review each of the following items one by one and address any issues as needed to ensure resolution.
    
    # Checklist for the Narrative
    - Do not include the date on the cover.
    - Ensure that each chapter from Chapter 2 onward contains at least 1,000 characters.
    - Is the story engaging throughout?
    - Are the transitions between chapters natural and seamless?
    - Is there overuse of similar phrases?
    - Is the length of each chapter relatively consistent, with all chapters exceeding 1000 characters?
    - Do the chapter titles accurately reflect the content of each chapter?
    - Is the table of contents properly reflected?
    # Checklist for LaTeX
    - Are there any LaTeX syntax errors?
    - Is the title correctly reflected in the following part: \fancyhead[RE,LO]{\textit{Novel Title}}?
    - Is \fancyhead[LE,RO]{\thepage} displayed correctly on all pages?
    - Are there duplicate headers (e.g., repeated \section{{Introduction}} or \end{{document}})?
    - Are any unescaped symbols present (e.g., shakespeare_char should be written as shakespeare\_char in the text)?
    - Are quotation marks properly closed and formatting consistent (e.g., no missing closing quotation marks or unmatched parentheses)?
    - Are environments closed correctly (e.g., use \end{{figure}} instead of </end{{figure}}>)?
    - Are unnecessary \newpage, \clearpage, or \cleardoublepage commands present?
    - Do not include anything other than chapter titles or section names within \chapter*{}.
    - Is the placement of \chapter or \section correct, with no extra spaces or page breaks before or after them?
    - Is the document class option changed from twoside to oneside where applicable?
    - Has \let\cleardoublepage\clearpage been added to suppress the generation of blank pages?
    """
    
    refinement_prompt = """
        Great job! Now criticize and refine only the chapter that you just wrote.\n
        Make this complete in this pass, do not leave any placeholders.\n\n
        Pay particular attention to fixing any errors such as:\n
    """ + error_list

    second_refinement_prompt = """
        Refine the novel to a polished, publication-ready state.
        Pay close attention to the overall flow and consistency with the story's themes.
        Identify redundant elements, such as repetitive descriptions or scenes, and determine where adjustments or removals are necessary to improve pacing.
        Look for opportunities to streamline the narrative, making it more concise while preserving its impact and atmosphere.
    """ + error_list 

    novel_prompt = f"""
    We are sharing the Overall Vision for the spin-off novel created by the editor, along with the first draft of the novel based on it.
    Please carefully interpret and understand these as they will be used for subsequent tasks.
    # Overall Vision:
    {idea_text}
    # First Draft
    {results["model_response"]}
    
    After thoroughly understanding the Overall Vision and the entire novel, expand upon the first draft to create a second version, ensuring that each chapter exceeds 1000 characters.

    However, at this stage, please finalize the structure of the chapters and their titles, and do not make any further changes to them. Additionally, ensure that the novel contains no more than five chapters.
    """
    coder_out = coder.run(novel_prompt)
    
    chapter_prompt = f"""
    Please double-check whether the structure and chapter names of the created novel comply with the following specifications.
    If they do not comply, review the overall text and make the necessary adjustments.
    # novel structure models
    - {idea["novel_structure_models"]}
    - Each chapter contains at least 1000 characters.
    - The division into chapters enhances the overall appeal of the novel.
    - The chapter titles appropriately reflect the content and are engaging enough to capture interest.
    
    If they do comply, no action is required.
    """
    coder_out = coder.run(novel_prompt)
        
    tex_prompt = """
    We've provided the `latex/template.tex` file to the project.
    
    First, appropriately reflect the novel's structure and chapter titles that were previously suggested into latex/template.tex.
    
    Before every paragraph, please include a brief description of what you plan to write in that paragraph in a comment.

    Be sure to first name the file and use *SEARCH/REPLACE* blocks to perform these edits.
    """
    coder_out = coder.run(tex_prompt)

    # CURRENTLY ASSUMES LATEX
    title_prompt = f"""
        We've provided the `latex/template.tex` file to the project. We will be filling it in section by section.

        First, please fill in the "Title", "Author" and "Table of Contents" sections of the writeup.

        Some tips are provided below:
            "Title":
                - "description": "Create a captivating and unique title that reflects the central theme or tone of the story.",
                - "condition": "The title should be between 10 and 30 characters."
            "Author":
                - "name": "AI author
                - "condition": "The author name must be 'AI author'."
            "Table of Contents"
                - "description":Ensure that each page corresponds to the correct chapter title.
                - "condition"Update the Table of Contents accordingly whenever other parts are modified.

        Before every paragraph, please include a brief description of what you plan to write in that paragraph in a comment.

        Be sure to first name the file and use *SEARCH/REPLACE* blocks to perform these edits.
        """
    coder_out = coder.run(title_prompt)
    coder_out = coder.run(
        refinement_prompt.replace(r"{{", "{").replace(r"}}", "}")
    )
    
    for section in range(5):
        section_prompt = f"""
        Please write each section in order from the beginning. 
        
        Once you finish writing one chapter, stop and wait for the next instructions.
        
        If all chapters have already been completed, 
        
        review the entire document and make any necessary additions or revisions where improvements can be made. 
        
        However, do not add new chapters or change the chapter titles under any circumstances.

        Before every paragraph, please include a brief description of what you plan to write in that paragraph in a comment.

        Be sure to first name the file and use *SEARCH/REPLACE* blocks to perform these edits.
        """
        coder_out = coder.run(section_prompt)
        coder_out = coder.run(
            refinement_prompt.replace(r"{{", "{").replace(r"}}", "}")
        )

    ## SECOND REFINEMENT LOOP
    coder.run("""
        Great job! Now that the novel is complete, 
        let’s refine each chapter one last time.
        # Check Points
        - Each chapter has a consistent word count and exceeds 1000 characters.
        - Each chapter title accurately reflects its content.
        - The chapters are well-connected, creating a cohesive and compelling novel overall.
        - Ensure that each page corresponds to the correct chapter title.
        However, when refining, do not modify the LaTeX formatting under any circumstances. Focus solely on improving the text content.
        """ + error_list
    )
    for section in range(2):
        coder_out = coder.run(
            second_refinement_prompt
            .replace(r"{{", "{")
            .replace(r"}}", "}")
        )

    generate_latex(coder, folder_name, f"{folder_name}/Spin-off_novel.pdf")


if __name__ == "__main__":
    from aider.coders import Coder
    from aider.models import Model
    from aider.io import InputOutput
    import json

    parser = argparse.ArgumentParser(description="Perform writeup for a project")
    parser.add_argument("--folder", type=str)
    parser.add_argument("--no-writing", action="store_true", help="Only generate")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-2024-05-13",
        choices=AVAILABLE_LLMS,
        help="Model to use for AI Scientist.",
    )
    args = parser.parse_args()
    client, client_model = create_client(args.model)
    print("Make sure you cleaned the Aider logs if re-generating the writeup!")
    folder_name = args.folder
    idea_name = osp.basename(folder_name)
    exp_file = osp.join(folder_name, "experiment.py")
    notes = osp.join(folder_name, "notes.txt")
    model = args.model
    writeup_file = osp.join(folder_name, "latex", "template.tex")
    ideas_file = osp.join(folder_name, "ideas.json")
    with open(ideas_file, "r") as f:
        ideas = json.load(f)
    for idea in ideas:
        if idea["Name"] in idea_name:
            print(f"Found idea: {idea['Name']}")
            break
    if idea["Name"] not in idea_name:
        raise ValueError(f"Idea {idea_name} not found")
    fnames = [exp_file, writeup_file, notes]
    io = InputOutput(yes=True, chat_history_file=f"{folder_name}/{idea_name}_aider.txt")
    if args.model == "deepseek-coder-v2-0724":
        main_model = Model("deepseek/deepseek-coder")
    elif args.model == "llama3.1-405b":
        main_model = Model("openrouter/meta-llama/llama-3.1-405b-instruct")
    else:
        main_model = Model(model)
    coder = Coder.create(
        main_model=main_model,
        fnames=fnames,
        io=io,
        stream=False,
        use_git=False,
        edit_format="diff",
    )
    if args.no_writing:
        generate_latex(coder, args.folder, f"{args.folder}/test.pdf")
    else:
        try:
            perform_writeup(idea, folder_name, coder, client, client_model)
        except Exception as e:
            print(f"Failed to perform writeup: {e}")
