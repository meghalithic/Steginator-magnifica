# Part of the standard library
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import re
import os.path
import math

# Not part of the standard library
import numpy as np
import pandas as pd
import cv2
import dlib
import pycocotools.mask as mask_util
from mmdet.core import encode_mask_results

# Tools for predicting objects and shapes in new images


def initialize_xml():
    root = ET.Element("dataset")
    root.append(ET.Element("name"))
    root.append(ET.Element("comment"))
    images_e = ET.Element("images")
    root.append(images_e)

    return root, images_e


def create_box(d, ignore=False):
    box = ET.Element("box")
    box.set("top", str(int(d.top())))
    box.set("left", str(int(d.left())))
    box.set("width", str(int(d.right() - d.left())))
    box.set("height", str(int(d.bottom() - d.top())))
    if ignore:
        box.set("ignore", "1")

    return box


def create_part(x, y, id):
    part = ET.Element("part")
    part.set("name", str(int(id)))
    part.set("x", str(int(x)))
    part.set("y", str(int(y)))

    return part


def pretty_xml(elem, out):
    et = ET.ElementTree(elem)
    root = et.getroot()
    string = ET.tostring(root)
    indent = "   "
    xmlstr = parseString(string).toprettyxml(indent=indent)
    with open(out, "w") as f:
        f.write(xmlstr)


# Importing to pandas tools


def natural_sort(l):
    convert = lambda text: int(text) if text.isdigit() else 0
    alphanum_key = lambda key: [convert(c) for c in re.split("([0-9]+)", key)]
    return sorted(l, key=alphanum_key)


def dlib_xml_to_pandas(xml_file: str):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    landmark_list = []
    for images in root:
        for image in images:
            for box in image:
                bbox = f"{box.attrib['top']}_{box.attrib['left']}_{box.attrib['width']}_{box.attrib['height']}"
                for parts in box:
                    if parts.attrib["name"] is not None:
                        data = {
                            "id": image.attrib["file"],
                            "box_id": bbox,
                            "box_top": float(box.attrib["top"]),
                            "box_left": float(box.attrib["left"]),
                            "box_width": float(box.attrib["width"]),
                            "box_height": float(box.attrib["height"]),
                            "X" + parts.attrib["name"]: float(parts.attrib["x"]),
                            "Y" + parts.attrib["name"]: float(parts.attrib["y"]),
                        }

                    landmark_list.append(data)
    dataset = pd.DataFrame(landmark_list)
    df = dataset.groupby(["id", "box_id"], sort=False).max()
    df = df[natural_sort(df)]
    df = df.reset_index()
    basename = os.path.splitext(xml_file)[0]
    df.to_csv(f"{basename}.csv")
    return df


def condition(x, img, pad, confidence):
    return (
        x[0] < pad[0]
        or x[1] < pad[1]
        or x[2] > (img[1] - pad[2])
        or x[3] > (img[0] - pad[3])
        or x[4] < confidence
    )


def autocondition(element, height, width, model, class_id, strict):
    bbox = mask_util.toBbox(element)
    maskedArr = mask_util.decode(element)
    # Find contours
    contours, _ = cv2.findContours(maskedArr, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnt = max(contours, key=cv2.contourArea)
    # Find moments
    M = cv2.moments(cnt)
    xc = int(M["m10"] / M["m00"])
    yc = int(M["m01"] / M["m00"])
    # Find area, perimeter, solidity, circularity, aspect ratio, and angle
    area = cv2.contourArea(cnt)
    perimeter = cv2.arcLength(cnt, True)
    circularity = 4 * math.pi * area / (perimeter * perimeter)
    # Find convex hull and solidity
    hull = cv2.convexHull(cnt)
    solidity = float(area) / cv2.contourArea(hull)
    rect = cv2.minAreaRect(cnt)
    (_, _), (d1, d2), angle = rect

    array = np.array([
            class_id,
            area,
            perimeter,
            solidity,
            circularity,
            min(d1, d2) / max(d1, d2),
            height,
            width,
            angle,
            xc,
            yc,
            int(bbox[0]),
            int(bbox[1]),
            int(bbox[2]),
            int(bbox[3]),
        ], dtype=float)

    prediction = model.predict_proba(array.reshape(1, -1))
    return True if prediction[0][0] > strict else False
