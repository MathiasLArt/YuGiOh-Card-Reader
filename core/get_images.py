import json
import os
import requests
import re
import time
import argparse

from logger import setup_logger


def download(card, output_dir, force=False): 
    if 'image_url' in card['card_images'][0]:
        name = re.sub(r'[\/\\?%*:|"<>]', '', card['name'])
        card_id = card['id']
        url = card['card_images'][0]['image_url']
        extension = url.split('.')[-1]

        image_path = os.path.join(output_dir, f'{card_id}.{extension}')

        if not force:
            # Check if the file already exists and skip if it does
            if os.path.exists(image_path):
                logger.info(f"Image for {card['name']} already exists, skipping download.")
                return

        try:
            response = requests.get(url, headers={'User-Agent': 'Your User Agent'})
            response.raise_for_status()  # Check for HTTP status code errors

            if response.status_code == 200:
                with open(image_path, 'wb') as img_file:
                    img_file.write(response.content)
                logger.info(f"Downloaded image for {card['name']}")
            else:
                logger.warning(f"Failed to download image for {card['name']} (HTTP status code: {response.status_code})")
        except Exception as e:
            logger.error(f"Error downloading image for {card['name']}: {str(e)}")


def main(args):
    # Create the directory if it doesn't exist
    card_dir = 'core/cards'
    os.makedirs(card_dir, exist_ok=True)

    # Read JSON data from file in the same directory as the script
    json_file = 'core\cardinfo.php'
    if not os.path.exists(json_file):
        print(f"File '{json_file}' not found in the current directory.")
        return

    with open(json_file, 'r') as file:
        data = json.load(file)['data']

    # Determine the number of entries
    num_entries = len(data)
    print(f"Number of entries in the JSON data: {num_entries}")

    # Start timing
    start_time = time.time()

    # Start downloading
    for key in range(num_entries):
        card = data[key]
        download(card, card_dir, force=args.force)
        time.sleep(0.5)

    # End timing
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f"Total time taken to download {num_entries} images: {total_time:.2f} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Skip the check for existing files')
    args = parser.parse_args()

    # Configure logger
    logger = setup_logger()

    main(args)
