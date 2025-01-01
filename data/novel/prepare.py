import argparse
from pathlib import Path
import requests
import zipfile
import io
import charset_normalizer
import os

def fetch_and_extract_zip(url):
    """
    Fetch a ZIP file from a URL and extract the content of the first text file found.

    This function downloads a ZIP file from the provided URL, searches for the first
    text file (.txt) within the archive, detects its encoding, and returns its content
    as a decoded string. If no text file is found, or if the download fails, an exception
    is raised.

    Args:
        url (str): The URL of the ZIP file to be downloaded.

    Returns:
        str: The decoded content of the first text file found in the ZIP archive.

    Raises:
        Exception: If the HTTP request fails or no text file is found in the archive.
    """
    response = requests.get(url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for filename in z.namelist():
                if filename.endswith('.txt'):
                    with z.open(filename) as file:
                        raw_data = file.read()
                        detected = charset_normalizer.detect(raw_data)
                        encoding = detected['encoding']
                        return raw_data.decode(encoding, errors='replace')
        raise Exception("No .txt file found in the ZIP archive.")
    else:
        raise Exception(f"Failed to fetch the ZIP file. Status code: {response.status_code}")

def save_text_content(content, output_file):
    """
    Save the provided content to a file.

    This function writes the given string content to a specified file. If the file
    cannot be written to, an exception is raised and an error message is displayed.

    Args:
        content (str): The text content to save to the file.
        output_file (Path): The path to the output file where the content will be saved.

    Raises:
        Exception: If an error occurs during the file writing process.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            out_file.write(content)
        print(f"Content saved to {output_file}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    """
    Main script to fetch a ZIP file from a URL, extract its content, and save it to a file.

    This script uses command-line arguments to specify the URL of a ZIP file and the
    name of the output file. It fetches the ZIP file, extracts the first text file found
    in the archive, and saves its content to the specified output file. The default
    settings fetch "Hashire Merosu" from Aozora Bunko and save it as "novel.txt".

    Note:
        The default URL is set to download from Aozora Bunko (https://www.aozora.gr.jp/),
        a Japanese digital library of free eBooks.

    Command-line Arguments:
        -u, --url (str): The URL of the ZIP file to download. Defaults to the URL for
                         "Hashire Merosu" from Aozora Bunko.
        -o, --output_file (str): The name of the output file to save the content to.
                                 Defaults to "novel.txt".

    Raises:
        Exception: If an error occurs during the fetch or save process.
    """
    parser = argparse.ArgumentParser(
        description="Fetch a ZIP file from a URL, extract its content, and save it to a file."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        default="https://www.aozora.gr.jp/cards/000035/files/1567_ruby_4948.zip",
        help="URL of the ZIP file. Default is Aozora Bunko's 'Hashire Merosu'."
    )
    parser.add_argument(
        "-o", "--output_file",
        type=str,
        default="novel.txt",
        help="Name of the output file. Default is 'novel.txt'."
    )

    args = parser.parse_args()

    try:
        # Fetch and extract the text content from the ZIP
        content = fetch_and_extract_zip(args.url)

        # Get the directory of the current script
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        output_file = script_dir / args.output_file

        # Save the entire content to a single file
        save_text_content(content, output_file)

    except Exception as e:
        print(f"An error occurred: {e}")