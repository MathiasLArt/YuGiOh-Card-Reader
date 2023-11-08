import cv2
import os
import numpy as np
from deskew import determine_skew
from skimage.transform import rotate
import json
from PIL import Image
import pytesseract
from fuzzywuzzy import fuzz, process
from core.utils import four_point_transform
import imutils


class CardProcessor:
    def load_image(self, image_path):
        if not os.path.exists(image_path) or not image_path.lower().endswith(
            (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif")
        ):
            print("Not a valid image path!")
            exit(0)

        img = cv2.imread(image_path)
        return img

    def resize_image(self, img):
        # Resizing to 1000x1000
        img_resized = cv2.resize(img, (750, 750))
        coef_y = img.shape[0] / img_resized.shape[0]
        coef_x = img.shape[1] / img_resized.shape[1]

        return (img_resized, coef_x, coef_y)

    def preprocess_image(self, args, img):
        # Grayscale -> Blurring -> Canny thresholding -> Dilation
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # if args.visualize:
        #     cv2.imshow("tweak", gray_img)
        #     cv2.waitKey(0)
        blur = cv2.GaussianBlur(gray_img, (9, 9), 0)
        # if args.visualize:
        #     cv2.imshow("tweak", blur)
        #     cv2.waitKey(0)
        thresh = cv2.Canny(blur, 50, 100)
        # if args.visualize:
        #     cv2.imshow("tweak", thresh)
        #     cv2.waitKey(0)
        dilated = cv2.dilate(thresh, np.ones((7, 9), dtype=np.int8))
        if args.visualize:
            cv2.imshow("tweak", dilated)
            cv2.waitKey(0)

        return dilated

    def merge_contours(self, contours):
        merged_contours = []

        for i, contour in enumerate(contours):
            is_inside = False
            for j, other_contour in enumerate(contours):
                if i != j:  # Avoid comparing the same contour with itself
                    # Get the centroid of the current contour
                    cx, cy = tuple(contour[0][0])

                    # Check if the centroid of the current contour is inside the other contour
                    if (
                        cv2.pointPolygonTest(
                            other_contour, (float(cx), float(cy)), False
                        )
                        > 0
                    ):
                        is_inside = True
                        break

            if not is_inside:
                merged_contours.append(contour)

        return merged_contours

    def extract_contours(self, dilated, img_resized, coef_x, coef_y, visualize=False):
        # Step 1: Detect contours in the dilated image
        contours = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        # Initialize a list to store quadrilateral contours
        tbd = list()

        # Step 2: Identify and store quadrilateral contours
        for c in contours:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.05 * peri, True)

            # if our approximated contour has four points, then we
            # can assume that we have found our screen
            if len(approx) == 4:
                tbd.append(approx)

        tbd = self.merge_contours(tbd)

        # Initialize a list to store new contours with associated text
        text_contours = list()

        # Step 3: Process each selected quadrilateral contour
        for c in tbd:
            # draw contours around detected card
            if visualize:
                cv2.drawContours(img_resized, [c], -1, (0, 255, 0), thickness=3)
                cv2.imshow("Contours", img_resized)
                cv2.waitKey(0)

            hull = cv2.convexHull(c)
            x, y, w, h = cv2.boundingRect(c)

            # Filter out large quadrilateral contours
            if h > 100 and w > 100:
                # Step 4: Warp the card region to a rectangle
                warped = four_point_transform(img_resized, c.reshape((4, 2)))
                warped_w = warped.shape[0]
                warped_h = warped.shape[1]

                if visualize:
                    cv2.imshow("warped", cv2.resize(warped, (750, 750)))
                    cv2.waitKey(0)

                # Determine angle for deskewing
                angle = determine_skew(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY))

                # Step 5: Deskew the region (if needed)
                if angle != 0 and angle is not None:
                    warped = rotate(warped, angle, resize=True)

                # Step 6: Crop a specific region of the warped image
                cropped = warped[
                    int(warped.shape[1] // 15) : int(warped.shape[1] // 7.7),
                    int(warped.shape[0] * 0.05) : int(warped.shape[0] * 0.75),
                ]
                text_roi = cv2.resize(cropped, (750, 90))

                if visualize:
                    cv2.imshow("extracted name", text_roi)
                    cv2.waitKey(0)

                # Step 7: Use OCR to extract text from the resized image
                text_roi = Image.fromarray((text_roi * 255).astype(np.uint8))
                query = pytesseract.image_to_string(text_roi, config="--psm 7")

                if query:
                    text_contours.append([c, query])

        # Return a list of new contours with associated text
        return text_contours

    def find_matching_cards(self, card_names, text_contours, min_similarity=70):
        # Find card names based on extracted text
        card_text_list = []

        card_names_list = [card["name"] for card in card_names["data"]]

        for c, query in text_contours:
            # Extract the 'name' property from each card object

            # Perform a fuzzy search with the specified minimum similarity
            matches = process.extract(query, card_names_list, scorer=fuzz.ratio)

            # Filter matches based on the minimum similarity threshold
            filtered_matches = [
                match for match in matches if match[1] >= min_similarity
            ]

            if filtered_matches:
                best_match = filtered_matches[0]  # Get the best match
                best_match_name = best_match[0]

                # Find the card object with the best matching 'name' property
                matching_card = None
                for card in card_names["data"]:
                    if card["name"] == best_match_name:
                        matching_card = card
                        break

                if matching_card:
                    card_text_list.append((c, matching_card))

        return card_text_list

    def draw_card_boxes(self, img, card_text_list, coef_x, coef_y):
        # Draw bounding boxes around cards and display the result
        for c, card_text in card_text_list:
            c[:, :, 0] = c[:, :, 0] * coef_x
            c[:, :, 1] = c[:, :, 1] * coef_y

            x, y, w, h = cv2.boundingRect(c)

            try:
                if card_text:
                    # Get the size of the text bounds
                    (text_w, text_h), _ = cv2.getTextSize(
                        card_text["name"], cv2.FONT_HERSHEY_COMPLEX_SMALL, 2, 3
                    )

                    # Define a padding value to make the rectangle larger
                    padding = 10

                    # Draw a white rectangle as the background with padding
                    cv2.rectangle(
                        img,
                        (x - padding, y - 15 - text_h - padding),
                        (x + text_w + padding, y - 15 + padding),
                        (255, 255, 255),
                        -1,
                    )
                    cv2.putText(
                        img,
                        card_text["name"],
                        (x, y - 15),
                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                        2,
                        (0, 0, 0),
                        3,
                    )
                    # draw the contours
                    cv2.drawContours(img, [c], -1, (255, 255, 255), thickness=3)
            except card_text.DoesNotExist:
                continue

        # cv2.imshow("img", img)
        cv2.imshow("img_res", cv2.resize(img, (750, 750)))
        cv2.waitKey(0)
