import cv2
import os
import numpy as np
from deskew import determine_skew
from skimage.transform import rotate
import json
import difflib
from PIL import Image
import argparse
import pytesseract
from fuzzywuzzy import fuzz, process

from core.utils import four_point_transform

def load_card_data(filename):
    # Load card data from a file (e.g., JSON)
    with open(filename, "rb") as f:
        card_data = json.loads(f.read())
    return card_data

def preprocess_image(args):

    image_path = args.image

    # Load the image and perform preprocessing steps
    if not os.path.exists(image_path) or not image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
        print("Not a valid image path!")
        exit(0)
    
    img = cv2.imread(image_path)

    # Resizing to 1000x1000
    img_resized = cv2.resize(img, (1000, 1000))
    coef_y = img.shape[0] / img_resized.shape[0]
    coef_x = img.shape[1] / img_resized.shape[1]

    # Grayscale -> Blurring -> Canny thresholding -> Dilation
    gray_img = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
    if args.visualize:
        cv2.imshow("tweak", gray_img)
        cv2.waitKey(0)
    blur = cv2.GaussianBlur(gray_img, (9, 9), 0)
    if args.visualize:
        cv2.imshow("tweak", blur)
        cv2.waitKey(0)
    thresh = cv2.Canny(blur, 50, 100)
    if args.visualize:
        cv2.imshow("tweak", thresh)
        cv2.waitKey(0)
    dilated = cv2.dilate(thresh, np.ones((11, 11), dtype=np.int8))
    if args.visualize:
        cv2.imshow("tweak", dilated)
        cv2.waitKey(0)

    return img, dilated,img_resized, coef_x, coef_y

def extract_text_from_card(image, dilated,img_resized, coef_x, coef_y, visualize=False):
    # Extract text from the card image

    contours, hierarchy = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    tbd = list()
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.05 * peri, True)
        if len(approx) == 4:
            tbd.append(approx)

    new_contours = list()

    for c in tbd:
        x, y, w, h = cv2.boundingRect(c)

        if (h > 100 and w > 100):
            warped = four_point_transform(img_resized, c.reshape((4, 2)) )
            warped_w = warped.shape[0]
            warped_h = warped.shape[1]
            # Determine angle for deskewing
            angle = determine_skew(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY))

            if angle != 0 and angle is not None:
                warped = rotate(warped, angle, resize=True)

            cropped = warped[int(warped.shape[1] // 16):int(warped.shape[1] // 7.7), int(warped.shape[0] * 0.05):int(warped.shape[0] * 0.73)]
            text_roi = cv2.resize(cropped, (1000, 70))

            if visualize:
                cv2.imshow("extracted name", text_roi)
                cv2.waitKey(0)

            text_roi = Image.fromarray((text_roi * 255).astype(np.uint8))

            query = pytesseract.image_to_string(text_roi, config="--psm 7")

            if query:
                new_contours.append([c, query])

    return new_contours

def find_matching_cards(card_names, new_contours, min_similarity=80):
    # Find card names based on extracted text
    card_text_list = []

    card_names_list = [card['name'] for card in card_names['data']]

    for c, query in new_contours:
        # Extract the 'name' property from each card object

        # Perform a fuzzy search with the specified minimum similarity
        matches = process.extract(query, card_names_list, scorer=fuzz.ratio)

        # Filter matches based on the minimum similarity threshold
        filtered_matches = [match for match in matches if match[1] >= min_similarity]

        if filtered_matches:
            best_match = filtered_matches[0]  # Get the best match
            best_match_name = best_match[0]

            # Find the card object with the best matching 'name' property
            matching_card = None
            for card in card_names['data']:
                if card['name'] == best_match_name:
                    matching_card = card
                    break

            if matching_card:
                card_text_list.append((c, matching_card))

    return card_text_list

def draw_card_boxes(img, card_text_list, coef_x, coef_y):
    # Draw bounding boxes around cards and display the result
    for c, card_text in card_text_list:
        c[:, :, 0] = c[:, :, 0] * coef_x
        c[:, :, 1] = c[:, :, 1] * coef_y

        x, y, w, h = cv2.boundingRect(c)

        try:
            if card_text:
                img = cv2.rectangle(
                    img, 
                    (x, y), 
                    (x + w, y + h), 
                    (0,200,0), 
                    3
                )

                #(w, h), _ = cv2.getTextSize(card_text['name'], cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)
                
                cv2.putText(
                    img, 
                    card_text['name'], 
                    (x, y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1.5, 
                    (0,200,0), 
                    3
                )
        except:
            continue

    cv2.imshow("img", img)
    cv2.imshow("img_res", cv2.resize(img, (500, 500)))
    cv2.waitKey(0)

def main(args):
    # Main script logic
    card_data = load_card_data("./core/cardinfo.php")
    img, dilated,image_resized, coef_x, coef_y = preprocess_image(args)

    new_contours = extract_text_from_card(img, dilated,image_resized, coef_x, coef_y, args.visualize)
    card_text_list = find_matching_cards(card_data, new_contours)
    
    draw_card_boxes(img, card_text_list, coef_x, coef_y)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="path to image")
    parser.add_argument("--tesseract", help="path to tesseract.exe")
    parser.add_argument("--visualize", help="boolean, visualize intermediate steps", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.tesseract) or not args.tesseract.lower().endswith(("tesseract.exe")):
        print("Not a valid tesseract executable!")
        exit(0)

    pytesseract.pytesseract.tesseract_cmd = args.tesseract

    main(args)
