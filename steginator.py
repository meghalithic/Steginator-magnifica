
# Base imports
import argparse
import os
import pickle

#3rd party
import cv2
import dlib
from mmdet.apis import init_detector, inference_detector

from utils import *


def main(args):

    # Initialize the segmentation model
    config_file = "./configs/swin/mask_config_serve.py"
    checkpoint_file = "./inference/deepbryo.pth"
    model = init_detector(config_file, checkpoint_file, device="cuda:0")

    # Load the xgboost model used for filtering
    autofilter = pickle.load(open("./inference/automated_filtering.dat", "rb"))

    # Load the dlib shape predictor
    shape_predictor = dlib.shape_predictor("./inference/landmark.dat")

    # Define the classes of interest and the extensions of the images
    extensions = {".jpg", ".jpeg", ".tif", ".png", ".bmp"}
    classes = [
        "autozooid",
        "orifice",
        "avicularium",
        "spiramen",
        "ovicell",
        "ascopore",
        "opesia",
    ]

    # Update the classes of the model
    model.CLASSES = tuple(classes[1:])

    # Initialize the output xml file
    root, images_e = initialize_xml()
    files = os.listdir(args["input_dir"])

    for filename in files:
        ext = os.path.splitext(filename)[1]
        if ext.lower() in extensions:

            print(f"Processing {filename}")
            path = os.path.join(args["input_dir"], filename)
            image_e = ET.Element("image")
            image_e.set("file", str(path))

            # loading image and histogram normalization
            input = os.path.join(args["input_dir"], filename)
            img = cv2.imread(input)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.bilateralFilter(img, 13, 75, 75)

            # Class id of interest
            idx = classes.index(args["class"])

            # Detection
            out = inference_detector(model, img)
            boxes = out[0][idx]
            masks = out[1][idx]
            encoded_masks = encode_mask_results(out[1])[idx]

            for item, bbox in enumerate(boxes):
                mask = masks[item]
                encoded_mask = encoded_masks[item]
                rect = dlib.rectangle(bbox[0], bbox[1], bbox[2], bbox[3])
                border = condition(bbox, img.shape, args["padding"], args["confidence"])
                if not border:
                    occluded = autocondition(encoded_mask, mask.shape[0], mask.shape[1], autofilter, idx, args["strictness"])
                    if not occluded:
                        box = create_box(rect)
                        shape = shape_predictor(img, rect)
                        part_length = range(0, shape.num_parts)
                        for item, i in enumerate(sorted(part_length, key=str)):
                            x = shape.part(item).x
                            y = shape.part(item).y
                            part = create_part(x, y, i)
                            box.append(part)
                        box[:] = sorted(box, key=lambda child: (child.tag, float(child.get("name"))))
                    else:
                        box = create_box(rect, ignore=True)
                else :
                    if bbox[4] > args["confidence"]:
                        box = create_box(rect, ignore=True)
                image_e.append(box)
            images_e.append(image_e)    
        # save the xml file
        output = os.path.join(args["out_dir"], "output.xml")
        pretty_xml(root, output)



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-i",
        "--input_dir",
        type=str,
        help="folder containing images to be predicted",
        required=True,
    )
    ap.add_argument(
        "-o",
        "--out-dir",
        type=str,
        help="output folder. if not specified, defaults to current directory",
        required=True,
    )
    ap.add_argument(
        "-c",
        "--class",
        type=str,
        default="autozooid",
        help="object class of interest. Options: all, autozooid, orifice, avicularium, ovicell, ascopore, opesia",
    )
    ap.add_argument(
        "-p",
        "--padding",
        nargs="+",
        type=float,
        default=[10, 10, 10, 10],
        help="remove objects falling within a certain distance from the image border. please provide it as a list in the following order: left, top, right, bottom ",
    )
    ap.add_argument(
        "-t",
        "--confidence",
        type=float,
        default=0.95,
        help="model's confidence threshold (default = 0.5)",
    )
    ap.add_argument(
        "-s",
        "--strictness",
        type=float,
        default=0.5,
        help="regulated the strictness of the automated filtering algorithm",
    )


    args = vars(ap.parse_args())
    main(args)
