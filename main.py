import argparse
import pytesseract
import os
from core.card_processing import CardProcessor
from core.data_loader import DataLoader


def main(args):
    # Load .php file contaiting all the necesairy card info.
    card_processor = CardProcessor()

    card_data = DataLoader.load_card_data(file="./core/cardinfo.php")

    img = card_processor.load_image(image_path=args.image)

    img_resized, coef_x, coef_y = card_processor.resize_image(img)
    dilated = card_processor.preprocess_image(args=args, img=img_resized)

    new_contours = card_processor.extract_contours(
        dilated=dilated,
        img_resized=img_resized,
        coef_x=coef_x,
        coef_y=coef_y,
        visualize=args.visualize,
    )

    card_list = card_processor.find_matching_cards(
        card_names=card_data, text_contours=new_contours, min_similarity=70
    )

    card_processor.draw_card_boxes(img, card_list, coef_x, coef_y)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="path to image")
    parser.add_argument("--tesseract", help="path to tesseract.exe")
    parser.add_argument(
        "--visualize", help="boolean, visualize intermediate steps", action="store_true"
    )
    args = parser.parse_args()
    if not os.path.exists(args.tesseract) or not args.tesseract.lower().endswith(
        ("tesseract.exe")
    ):
        print("Not a valid tesseract executable!")
        exit(0)
    pytesseract.pytesseract.tesseract_cmd = args.tesseract
    main(args)
